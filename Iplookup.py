import requests

def ip_lookup(ip):
    url = f"https://api.ipgeolocation.io/ipgeo?apiKey=YOUR_API_KEY&ip={ip}"  
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print("IP Information:")
        print(f"IP: {data['ip']}")
        print(f"Country: {data['country_name']}")
        print(f"Region: {data['state_prov']}")
        print(f"City: {data['city']}")
        print(f"Zip Code: {data['zipcode']}")
        print(f"Latitude: {data['latitude']}")
        print(f"Longitude: {data['longitude']}")
        print(f"Address: {data['continent_name']}, {data['country_name']}, {data['state_prov']}, {data['city']}")
    else:
        print("Failed to retrieve IP information.")

# 
ip = input("Enter an IP address: ")
ip_lookup(ip)
