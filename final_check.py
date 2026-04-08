import requests

# This is the direct API URL
URL = "https://abeyjohnpramod-supermarket-food-rescue.hf.space"
headers = {"User-Agent": "Mozilla/5.0"}

def validate():
    print(f"Checking status for: {URL}")
    try:
        # 1. Health Check
        r_health = requests.get(f"{URL}/health", headers=headers)
        if r_health.status_code == 200:
            print(f"✅ [1/3] System Health: OK")
        else:
            print(f"❌ [1/3] Health Check failed (Status: {r_health.status_code})")
            return

        # 2. Metadata Check
        r_meta = requests.get(f"{URL}/metadata", headers=headers)
        if r_meta.status_code == 200:
            print(f"✅ [2/3] Metadata: Found {r_meta.json().get('name')}")
        else:
            print(f"❌ [2/3] Metadata failed")

        # 3. Environment Logic Check (The big one!)
        r_reset = requests.post(f"{URL}/reset", json={}, headers=headers)
        if r_reset.status_code == 200:
            print(f"✅ [3/3] Environment Logic: Reset Successful!")
            print("\n" + "="*30)
            print("   FINAL STATUS: PASSED")
            print("="*30)
            print("Your Space is LIVE and ready for submission.")
        else:
            print(f"❌ [3/3] Logic Test failed (Status: {r_reset.status_code})")
            print(f"Error detail: {r_reset.text}")

    except Exception as e:
        print(f"❌ Script Error: {e}")

if __name__ == "__main__":
    validate()