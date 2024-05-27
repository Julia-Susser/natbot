from playwright.sync_api import sync_playwright
import time
from sys import argv, exit, platform
from openai import OpenAI
import os
import crawler
from bs4 import BeautifulSoup
from dotenv import load_dotenv


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class main():
    def __init__(self):
        file = open('action_prompt_template.txt', 'r', encoding='utf-8')
        self.prompt_template = file.read()
        self._crawler = crawler.Crawler()
        file = open('instructions_prompt.txt', 'r', encoding='utf-8')
        self.instructions = file.read()
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "system", "content":self.instructions},
        ]
        print(self.messages)


        self.objective = "Researching educational resources and multimedia content relevant to the Algebra 2."
        self.output_format = "Digital collection of links and references stored in an online document."
        file = open('starter_output.txt', 'r', encoding='utf-8')
        self.output= file.read()
        pass

    def write_output(self):
        url = self._crawler.page.url
        html_content = self._crawler.page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        plain_text = soup.get_text().replace("\n", " ")
        message = f"""
        write an output to finish {self.objective} and output {self.output_format} given that you already have {self.output}
        You are currently at {url} and have the following information \n
        {plain_text}
        """

        print(message)
        response = client.chat.completions.create(model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message},
        ],
        temperature=0.5,
        n=1,  # Assuming you want only one response
        max_tokens=1000)
        print(response)
        w = response.choices[0].message.content
        file = open("output.txt", "w")
        file.write(str(w))

    def make_decision(self):
        #run open_ai
        prompt = self.prompt_template
        prompt = prompt.replace("$objective", self.objective)
        prompt = prompt.replace("$output_format", self.output_format)
        url = self._crawler.page.url
        prompt = prompt.replace("$url", url[:100])
        prompt = prompt.replace("$previous_command", self.prev_command)
        browser_content = "\n".join(self._crawler.crawl())
        prompt = prompt.replace("$browser_content", browser_content[:7500])
        prompt = prompt.replace("$current_output", self.output)

        self.messages = self.messages + [
                    {"role": "user", "content": prompt}
        ]


        print(self.messages)
        print(prompt)
        while True:
            try:
                response = client.chat.completions.create(model="gpt-4",
                messages=self.messages,
                temperature=0.5,
                n=1,  # Assuming you want only one response, not 3 as before
                max_tokens=50)
                response = response.choices[0].message.content
                break
            except openai.RateLimitError as e:
                print("Rate Limit Exceeded. Retrying in 5 seconds...")
                time.sleep(5)


        #overide
        if len(response) > 0:
            print("Suggested command: " + response)
        q = input("would you like to override command?")
        if len(q) > 0:
            response = q
        self.messages.append( {"role": "system", "content": response})
        return response


    def run_cmd(self,cmd):
        if "COMPLETE STEP" not in cmd:
            self.prev_command = cmd
            self.prev_url = self._crawler.page.url

        cmd = cmd.split("\n")[0].strip()
        if "SCROLL" in cmd:
            direction = cmd.split(" ")[1].upper()
            self._crawler.scroll(direction)
        elif "CLICK" in cmd:
            id = cmd.split(" ")[1]
            self._crawler.click(id)
        elif "SEARCH" in cmd:
            query = "+".join(cmd.split(" ")[1:]).strip('"')
            self._crawler.go_to_page("https://www.google.com/search?q=" + query)
        elif "TYPE" in cmd:
            id, text = cmd.split(" ")[1], " ".join(cmd.split(" ")[2:])
            text = text.strip('"')  # Remove quotes if present
            self._crawler.type(id, text)
        elif "GO BACK" in cmd:
            self._crawler.go_to_page(self.prev_url)
        elif "GO TO" in cmd:
            url = cmd.split(" ")[1]
            self._crawler.go_to_page(url)
        elif "COMPLETE STEP" in cmd:
            while True:
                try:
                    response = self.write_output()
                    break
                except openai.RateLimitError as e:
                    print("Rate Limit Exceeded. Retrying in 5 seconds...")
                    time.sleep(5)
            return 
        time.sleep(2)




    def run(self):
        self._crawler.go_to_page("https://google.com")
        self.prev_command = "GO https://google.com"
        self.prev_url = "https://google.com"
        while True:
            cmd = self.make_decision()
            self.run_cmd(cmd)
            pass


if __name__ == "__main__":
    task_runner = main()
    task_runner.run()