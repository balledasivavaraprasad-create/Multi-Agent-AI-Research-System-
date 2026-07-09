import os
import getpass
from huggingface_hub import HfApi

files_to_upload = [
    "agents.py",
    "server.py",
    "pipeline.py",
    "requirements.txt",
    "Dockerfile",
    "tools.py",
    "README.md",
    "render.yaml"
]

print("🚀 Hugging Face Space File Uploader")
print("This script will upload your local backend files directly to your HF Space: itzSiva1/AdvancedMultiAgentSystem\n")

hf_token = getpass.getpass("Enter your Hugging Face WRITE token: ").strip()

if not hf_token:
    print("❌ Token cannot be empty!")
    exit(1)

api = HfApi()

try:
    print("\nValidating token and space repository...")
    # Attempt to fetch repo info to verify access
    repo_info = api.repo_info(repo_id="itzSiva1/AdvancedMultiAgentSystem", repo_type="space", token=hf_token)
    print(f"✅ Access verified to Space: {repo_info.id}")
    
    print("\nUploading files...")
    for file_name in files_to_upload:
        if os.path.exists(file_name):
            print(f"📤 Uploading {file_name}...")
            api.upload_file(
                path_or_fileobj=file_name,
                path_in_repo=file_name,
                repo_id="itzSiva1/AdvancedMultiAgentSystem",
                repo_type="space",
                token=hf_token
            )
            print(f"✅ Successfully uploaded {file_name}")
        else:
            print(f"⚠️ Warning: {file_name} not found locally, skipping.")
            
    print("\n🎉 All files successfully uploaded to Hugging Face Space!")
    print("The space will now automatically build and start the Gemini-enabled backend.")
except Exception as e:
    print(f"\n❌ Error during upload: {e}")
