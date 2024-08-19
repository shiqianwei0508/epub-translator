import requests
import time
import argparse
import logging

logging.basicConfig(level=logging.INFO)

class ClashOperator:
    def __init__(self, api_url, api_token, group_name, delay):
        self.api_url = api_url
        self.api_token = api_token
        self.group_name = group_name
        self.delay = delay

    def get_proxy_group(self):
        try:
            response = requests.get(f"{self.api_url}/proxies", headers={'Authorization': f"Bearer {self.api_token}"})
            response.raise_for_status()

            groups = response.json()['proxies']
            return groups.get(self.group_name, None)

        except requests.exceptions.RequestException as e:
            logging.error("获取代理组失败: %s", e)
            return None

    def switch_proxy_in_group(self, proxy_name):
        payload = {"name": proxy_name}
        try:
            response = requests.put(f"{self.api_url}/proxies/{self.group_name}", json=payload,
                                     headers={'Authorization': f"Bearer {self.api_token}"})
            response.raise_for_status()

            logging.info(f"成功切换到代理节点: '{proxy_name}'")

        except requests.exceptions.RequestException as e:
            logging.error("切换代理节点失败: %s", e)

    def cycle_proxies(self):
        group = self.get_proxy_group()
        if group:
            proxies = group.get('all', [])
            while True:
                for proxy in proxies:
                    self.switch_proxy_in_group(proxy)
                    # 倒计时显示
                    for remaining in range(self.delay, 0, -1):
                        print(f"切换到下一个代理节点还有 {remaining} 秒...", end='\r')
                        time.sleep(1)
                    print()  # 打印换行

def main():
    parser = argparse.ArgumentParser(description='切换 Clash 代理节点')
    parser.add_argument('--api-url', type=str, default='http://localhost:9090', help='Clash API 地址')
    parser.add_argument('--api-token', type=str, help='Clash API Token（如果需要的话）')
    parser.add_argument('--group-name', type=str, required=True, help='要切换的代理组名称')
    parser.add_argument('--delay', type=int, default=30, help='切换延迟（秒）')

    args = parser.parse_args()
    clash_operator = ClashOperator(args.api_url, args.api_token, args.group_name, args.delay)
    clash_operator.cycle_proxies()


if __name__ == "__main__":
    main()
