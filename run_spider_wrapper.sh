#!/bin/bash

spider_name=""
spider_args=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -n)
            shift
            spider_name=$1
            ;;
        -*)
            spider_args+=("$1")
            shift
            if [ $# -gt 0 ] && [[ $1 != -* ]]; then
                spider_args+=("$1")
            fi
            ;;
        *)
            break
            ;;
    esac
    shift
done

if [ -z "$spider_name" ]; then
    echo "Usage: $0 -n <spider_name> [spider_args...]" >&2
    exit 1
fi

run_spider() {
    output=$(PYTHONUNBUFFERED=1 scrapy crawl "$spider_name" "${spider_args[@]}" 2>&1 | tee >(cat - >&2))
    echo "$output"
}

postprocess_scrapy_log() {
    log="$1"
    pattern="INFO: Dumping Scrapy stats:.*"
    if [[ $log =~ $pattern ]]; then
        extracted_info="${BASH_REMATCH[0]}"
        echo "$extracted_info"
    else
        echo "Error postprocessing Scrapy log!"
    fi
}

send_request() {
    spider_name="$1"
    output="$2"
    url="https://ntfy.sh/spiders"
    # credentials="basic_auth_username:basic_auth_password"
    curl -X POST "$url" -d "Finished at $(date)\nOutput: $output" -H "title: Scrapy spider $spider_name finished!" -H "Authorization: Basic $(echo -n "$credentials" | base64)"
}

# Run the Scrapy spider
output=$(run_spider)
# Send a request after the spider finishes
send_request "$spider_name" "$(postprocess_scrapy_log "$output")"
