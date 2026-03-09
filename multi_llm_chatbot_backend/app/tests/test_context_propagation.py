# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All Rights Reserved 2008-2025
# Licensed under the BSD 3-Clause License
# https://opensource.org/licenses/BSD-3-Clause
#
# Copyright (c) 2008-2025, Neongecko.com Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import requests
import time

BASE_URL = "http://localhost:8000"

def test_unified_chat():
    print("\nSending unified chat request to /chat...\n")
    payload = {
        "user_input": "I'm a second year PhD student in Machine Learning. Any advice for my research paper presentation? I am preparing for final QnA session."
    }

    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return

    data = response.json()
    print(f"Type: {data.get('type')}")
    print(f"Collected Info: {data.get('collected_info')}")

    for reply in data.get("responses", []):
        print(f"\n{reply['persona']}:\n{reply['response'][:500]}...\n")  # show only first 500 chars

def test_context_log():
    print("\nFetching /context...\n")
    try:
        response = requests.get(f"{BASE_URL}/context")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Error fetching context:", e)
        return

    context = response.json()
    for entry in context[-6:]:  # Show the last 6 interactions for relevance
        print(f"{entry['role']}: {entry['content'][:120]}...")  # preview each entry

if __name__ == "__main__":
    test_unified_chat()
    time.sleep(2)
    test_context_log()
