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

# Set your file path here
file_path = "C:/Projects/Neon AI Project/Neon-AI-Project/multi_llm_chatbot_backend/app/tests/Resume.pdf"

# Step 1: Upload the file
upload_url = "http://localhost:8000/upload-document"
with open(file_path, "rb") as file:
    files = {"file": ("Resume.pdf", file, "application/pdf")}
    #print("Received file type:", file.content_type)
    upload_response = requests.post(upload_url, files=files)

print("Upload Status:", upload_response.status_code)
print("Upload Response:", upload_response.json())

# Step 2: Fetch context
context_url = "http://localhost:8000/context"
context_response = requests.get(context_url)

print("\nSession Context Status:", context_response.status_code)
print("Latest Context Snippet:")
for msg in context_response.json()[-3:]:  # Show last 3 entries
    print(msg)
