# Ntfy-Scrapy

Non-invasive wrapper around the 'scrapy crawl' command to send [ntfy](https://ntfy.sh/) notifications.

***Configure your endpoint and other parameters. (By default its ntfy.sh/spiders)***

***Your endpoint needs to have attachments enabled if you're sending data bigger than 4,096 bytes as per the [ntfy docs](https://docs.ntfy.sh/publish/#attachments)!***

### Description
Automates the execution of a Scrapy spider. It captures the spider's output and post-processes the Scrapy log to extract relevant information. Finally, it sends a request containing the spider's completion information.

Only useful if you can't or don't want to interact with (modify) the spider code. Otherwise, just make your requests in close method (or something similar).

Both scripts do the same thing.
***

***Example notification in ntfy web:***
![Home page](https://i.ibb.co/b6cG8WT/image.png|width=50)

### Bash Script

```bash
./run_spider_wrapper.sh -n <spider_name> [spider_args...]

    -n <spider_name>: Specifies the name of the Scrapy spider to run.
    [spider_args...]: Additional arguments to pass to the Scrapy spider.
```

### Python Script

```python
python run_spider_wrapper.py <spider_name> [spider_args...]
```
