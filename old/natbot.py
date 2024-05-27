#!/usr/bin/env python3
#
# natbot.py
#
# Set OPENAI_API_KEY to your API key, and then run this from a terminal.
#

from playwright.sync_api import sync_playwright
import time
from sys import argv, exit, platform
import openai
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
import os
import crawler
from bs4 import BeautifulSoup

quiet = False
if len(argv) >= 2:
    if argv[1] == '-q' or argv[1] == '--quiet':
        quiet = True
        print(
            "Running in quiet mode (HTML and other content hidden); \n"
            + "exercise caution when running suggested commands."
        )

class RunTask:
    def __init__(self):
        # Initialize action prompt template
        with open('action_prompt_template.txt', 'r', encoding='utf-8') as file:
            self.prompt_template = file.read()

        # Initialize evaluation prompt template
        with open('evaluation_prompt_template.txt', 'r', encoding='utf-8') as file:
            self.eval_prompt_template = file.read()

        # Set the OpenAI API key
        self._crawler = crawler.Crawler()

    def print_help(self):
        print(
            "(g) to visit url\n(u) scroll up\n(d) scroll down\n(c) to click\n(t) to type\n"
            + "(h) to view commands again\n(r/enter) to run suggested command\n(o) change objective"
        )

    def get_gpt_command(self, objective, url, previous_command, browser_content):
        prompt = self.prompt_template.replace("$objective", objective)
        prompt = prompt.replace("$url", url[:100])
        prompt = prompt.replace("$previous_command", previous_command)
        prompt = prompt.replace("$browser_content", browser_content[:4500])
        response = client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        n=1,  # Assuming you want only one response, not 3 as before
        max_tokens=50)

        return response.choices[0].message.content

    def evaluate_completion(self, objective, url, previous_command, browser_content):
        prompt = self.eval_prompt_template.replace("$objective", objective)
        prompt = prompt.replace("$url", url[:100])
        prompt = prompt.replace("$previous_command", previous_command)
        prompt = prompt.replace("$browser_content", browser_content[:4500])
        response = client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        n=1,  # Assuming you want only one response
        max_tokens=50)
        print(prompt)
        return response.choices[0].message.content


    def write_output(self,objective, browser_content):
        response = client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "write an output to finish "+objective+" using "+browser_content[:100]},
        ],
        temperature=0.5,
        n=1,  # Assuming you want only one response
        max_tokens=400)
        print(response)
        w = response.choices[0].message.content
        file = open("output.txt", "w")
        file.write(str(w))

    def run_cmd(self, cmd, objective):
        # You will need to define or pass _crawler instance appropriately
        cmd = cmd.split("\n")[0].strip()

        if cmd.startswith("SCROLL UP"):
            self._crawler.scroll("up")
        elif cmd.startswith("SCROLL DOWN"):
            self._crawler.scroll("down")
        elif cmd.startswith("CLICK"):
            commasplit = cmd.split(",")
            id = commasplit[0].split(" ")[1]
            self._crawler.click(id)
        elif cmd.startswith("SEARCH"):
            spacesplit = cmd.split(" ")
            text = spacesplit[2:]
            query = "+".join(text)
            self._crawler.go_to_page("https://www.google.com/search?q=" + query)
        elif cmd.startswith("TYPE"):
            spacesplit = cmd.split(" ")
            id = spacesplit[1]
            text = " ".join(spacesplit[2:])
            text = text.strip('"')  # Remove quotes if present
            self._crawler.type(id, text)
        elif cmd.startswith("GO"):
            spacesplit = cmd.split(" ")
            url = spacesplit[0].split(" ")[1]
            self._crawler.go_to_page(url)
        elif cmd.startswith("WRITE OUTPUT"):
            html_content = self._crawler.page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            plain_text = soup.get_text()
            while True:
                try:
                    response = self.write_output(objective, plain_text)
                    break
                except openai.RateLimitError as e:
                    print("Rate Limit Exceeded. Retrying in 5 seconds...")
                    time.sleep(5)
            return 

        time.sleep(2)
        html_content = self._crawler.page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        plain_text = soup.get_text()
        url = self._crawler.page.url
        with open("transcript.txt", "a") as f:
            f.write(f"Command: {cmd}\n")
            f.write(f"URL: {url}\n")
            f.write("Page Content:\n")
            plain_text = plain_text.replace("\n", "")
            f.write(plain_text + "\n")
            f.write("=" * 50 + "\n")  

        time.sleep(2)

    def run(self):
        # if there is alink then go directly to the link
        #objectives = ["I am middle school teacher. Write math curriculum about integer factorization", "write the words 'hello' to texteditor", "find donal trump's wikipedia", "Make a reservation for 2 at 7pm at bistro vida in menlo park", "go to google docs"]
        objectives = [
            "Buy math textbook on amazon",
            "Find Relevant Information on middle school science on prime number math on wikipedia",
            "Draft curriculum using information"
        ]
        i = 0
        objective = objectives[0]
        gpt_cmd = ""
        prev_cmd = ""
        query = "+".join(objective.split(" "))
        self._crawler.go_to_page("https://google.com")

        try:
            while True:
                browser_content = "\n".join(self._crawler.crawl())
                prev_cmd = gpt_cmd

                print("URL: " + self._crawler.page.url)
                print("Objective: " + objective)
                print("----------------\n" + browser_content + "\n----------------\n")

                while True:
                    try:
                        response = self.evaluate_completion(objective, self._crawler.page.url, prev_cmd,browser_content)
                        break
                    except openai.RateLimitError as e:
                        print("Rate Limit Exceeded. Retrying in 5 seconds...")
                        time.sleep(5)


                print("Completion:" + response)
                q = input("would you like to override completion?")
                if len(q) > 0:
                    response = q
                if response == "TRUE":
                    i = i + 1
                    objective = objectives[i]

                while True:
                    try:
                        gpt_cmd = self.get_gpt_command(objective, self._crawler.page.url, prev_cmd, browser_content)
                        break
                    except openai.RateLimitError as e:
                        print(e)
                        print("Rate Limit Exceeded. Retrying in 5 seconds...")
                        time.sleep(5)


                gpt_cmd = gpt_cmd.strip()
                if len(gpt_cmd) > 0:
                    print("Suggested command: " + gpt_cmd)
                q = input("would you like to override command?")
                if len(q) > 0:
                    gpt_cmd = q
                self.run_cmd(gpt_cmd, objective)



        except KeyboardInterrupt:
            print("\n[!] Ctrl+C detected, exiting gracefully.")
            exit(0)



if __name__ == "__main__":
    task_runner = RunTask()
    task_runner.run()
