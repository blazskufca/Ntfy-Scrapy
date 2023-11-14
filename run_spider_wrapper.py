#! /usr/bin/env python
# -*- coding: utf-8 -*-

import signal
from os import environ
from io import StringIO
from requests import post
from base64 import b64encode
from datetime import datetime
from sys import stdout, getsizeof
from threading import Thread, Lock
from subprocess import CalledProcessError, Popen, PIPE
from re import Match, Pattern, DOTALL, search, compile
from argparse import ArgumentParser, REMAINDER, Namespace
from typing import Optional, TextIO, List, Iterable, IO, AnyStr, Dict, Any

NTFY_INSTANCE_ADDRESS: str = environ.get("ntfy_instance_address", "ntfy.sh")
NTFY_TOPIC: str = environ.get("ntfy_topic", "spiders")
NTFY_USERNAME: Optional[str] = environ.get("ntfy_username")
NTFY_PASSWORD: Optional[str] = environ.get("ntfy_password")
NTFY_BEARER: Optional[str] = environ.get("ntfy_bearer")
RED_COLOR: str = "\033[91m"
END_COLOR: str = "\033[0m"


class Tee(StringIO):
    """Duplicate output to stdout and a string buffer, which will be then parsed."""

    def __init__(self) -> None:
        super().__init__()
        self.stdout: TextIO = stdout
        self.file: StringIO = StringIO()
        self.lock: Lock = Lock()

    def close(self) -> str:
        with self.lock:
            str_buffer: str = self.file.getvalue()
            self.file.close()
            return str_buffer

    def write(self, data: str) -> None:
        with self.lock:
            super().write(data)
            self.file.write(data)
            self.stdout.write(data)
            self.stdout.flush()

    def fileno(self) -> int:
        """Provide a fileno() method like a real file object."""
        return stdout.fileno()

    def capture_output(self, source: Optional[IO[AnyStr]], *args: Any, **kwargs: Any) -> None:
        for line in iter(source.readline, ''):
            self.write(line)


def run_spider(spider_name: str, spider_args: Optional[Iterable[str]] = None) -> Optional[str]:
    process: Optional[Popen] = None
    tee: Optional[Tee] = None
    try:
        # Construct the command to run the Scrapy spider
        # Set log level to info, because that is more than enough to get dumped stats + smaller str buffer
        command: List[str] = ['scrapy', 'crawl', spider_name, "-L", "INFO"]

        # Add any additional arguments for the spider
        if spider_args:
            command.extend(spider_args)

        # Run the spider and capture the output in real-time
        tee: Tee = Tee()
        with Popen(
                command,
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
        ) as process:
            # Create threads for capturing stdout and stderr
            stdout_thread: Thread = Thread(target=tee.capture_output, args=(process.stdout, ))
            stderr_thread: Thread = Thread(target=tee.capture_output, args=(process.stderr, ))
            stdout_thread.start()
            stderr_thread.start()
            process.wait()
            stdout_thread.join()
            stderr_thread.join()

    except CalledProcessError as e:
        print(f"{RED_COLOR}ERROR: {e}{END_COLOR}")
    finally:
        if process and hasattr(process, 'pid'):
            # Kill the Scrapy spider if it's still running
            print(f"{RED_COLOR}Process {process.pid} is still running although it shouldn't, sending it"
                  f" SIGINT{END_COLOR}")
            process.send_signal(signal.SIGINT)
            process.wait()
        if tee and isinstance(tee, Tee):
            return tee.close()
        else:
            return "Error running Scrapy spider!"


def postprocess_scrapy_log(log: Optional[str] = None) -> AnyStr:
    pattern: Pattern[AnyStr] = compile(r'INFO: Dumping Scrapy stats:.*', DOTALL)
    match: Optional[Match] = None
    if log is not None:
        match = search(pattern, log)
    if match:
        extracted_info: AnyStr = match.group(0)
        return extracted_info
    else:
        return "Error postprocessing Scrapy log!"


def send_request(spider_name: str, output_arg: AnyStr, instance_address: str = NTFY_INSTANCE_ADDRESS,
                 topic: str = NTFY_TOPIC, username: Optional[str] = NTFY_USERNAME,
                 password: Optional[str] = NTFY_PASSWORD, bearer: str = NTFY_BEARER) -> Optional[None]:
    url: str = f"https://{instance_address}/{topic}"
    headers: Dict[str] = dict(title=f"Scrapy spider {spider_name} finished!")

    if username and password:
        credentials: str = f"{username}:{password}"
        headers['Authorization'] = f"Basic {b64encode(credentials.encode('utf-8')).decode('utf-8')}"
    if bearer:
        headers['Authorization'] = f"Bearer {bearer}"
    if isinstance(output_arg, bytes):
        output_arg = output_arg.decode('utf-8')
    if (byte_size := getsizeof(output_arg)) >= 4096:
        headers["filename"] = f"{spider_name}.log"
        print(f"{RED_COLOR}WARNING: You'll receive your log as an attachment, because it's {byte_size} bytes long."
              f"{END_COLOR}")

    data: str = f"Finished at {datetime.now()} Output: {output_arg}"

    post(
        url,
        data=data.encode('utf-8'),
        headers=headers
    ).raise_for_status()


if __name__ == "__main__":
    # Set up command line argument parsing
    parser: ArgumentParser = ArgumentParser(
        description='Run a Scrapy spider and send a request afterwards.')
    parser.add_argument('spider_name', help='Name of the Scrapy spider to run')
    parser.add_argument('spider_args', nargs=REMAINDER, help='Arguments for the spider')

    # Parse the command line arguments
    args: Namespace = parser.parse_args()

    # Run the Scrapy spider
    output: Optional[str] = run_spider(args.spider_name, args.spider_args)

    # Send a request after the spider finishes
    send_request(args.spider_name, postprocess_scrapy_log(output))
