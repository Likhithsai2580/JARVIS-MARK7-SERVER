import requests

class DeepSeek:
    def __init__(self):
        self.headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,en-IN;q=0.8",
            "authorization": "Bearer DosO8UA6vd/e+xGHJ0qG//CqwybHyG4HvSPiDehLTIrWc0ZO1tIlJhS+gU4r9wuy",
            "content-length": "189", 
            "content-type": "application/json",
            "cookie": "smidV2=20241202200243b36594e9064d922ffcf2165b223764ec002c6d2aea29e9b10; _frid=ac0327ffb1c74a7694782ba641c59508; .thumbcache_6b2e5483f9d858d7c661c5e276b6a6ae=HwtE/4lMhPiSEIHP1Acb1y3uOpVPlfda7JkZ+b0eK7OxwZRqx1AYeFyMJDmAUmzZ+j5Zo/l+aNR6ilG+TBHgsg%3D%3D; intercom-device-id-guh50jw4=724c9b8f-b138-4f17-b46f-dd0074ee7855; HWWAFSESID=4f471bead60e5a8b5c; HWWAFSESTIME=1735397134285; ds_session_id: 67f5f4d4acf14e6285f2404700c2b69d; ds_session_id=e9ed814dcfe940698170dfdf2c3d07f7; intercom-session-guh50jw4=bzBFNmhWOGRPYytDcUpkNzE0TStOUU5qaTkzOVRKZThKTmxQRkliazVpZHZxU1FVdEFRdy9Zd0NXdHVRVU9jQS0tZnZSMDNDOS9yMi9jTE5NR3lKL2ZrQT09--3c1d9ac094b6da3fb0b34c2fd152b9bcce88a7a7; __cf_bm=OBRv.5VRGfPXlhyhc52LJKtQel53CN2TTHx4auaT88E-1735397142-1.0.1.1-oORS9lI0sk2aTrVEwOQZ4Vij8L6JqC7UTXYDbpz82cVtJYpNqjA2cB9XF0dHMvibt84lxXSZ9B_kbMTAeAzusA",
            "origin": "https://chat.deepseek.com",
            "priority": "u=1, i",
            "referer": "https://chat.deepseek.com/",
            "sec-ch-ua": "\"Not A(Brand\";v=\"8\", \"Chromium\";v=\"132\", \"Microsoft Edge\";v=\"132\"",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "\"Android\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors", 
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36 Edg/132.0.0.0",
            "x-app-version": "20241129.1"
        }
        self.base_url = "https://chat.deepseek.com/api/v0"
        self.session_data = None

    def create_session(self):
        """Create a new chat session"""
        url = f"{self.base_url}/chat_session/create"
        payload = {"agent": "chat"}
        
        response = requests.post(url, headers=self.headers, json=payload)
        response_json = response.json()
        
        if response_json['code'] == 0:  # Assuming 0 is success code
            self.session_data = response_json['data']['biz_data']
            return self.session_data
        else:
            raise Exception(f"Failed to create session: {response_json['msg']}")

    def chat(self, prompt, parent_message_id=None, thinking_enabled=False, search_enabled=False, challenge_response=None):
        """Send a chat message"""
        if not self.session_data:
            raise Exception("No active session. Call create_session() first.")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "chat_session_id": self.session_data['id'],
            "parent_message_id": parent_message_id or self.session_data['current_message_id'],
            "prompt": prompt,
            "ref_file_ids": [],
            "thinking_enabled": thinking_enabled,
            "search_enabled": search_enabled,
            "challenge_response": challenge_response
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return response.json()

