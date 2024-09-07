from flask import Flask, render_template, request, jsonify
import requests
import matplotlib.pyplot as plt
import threading
import time
import io
import base64
app = Flask(__name__)


ship_speed = []
ship_course = []
ship_position = {'lat': 0.0, 'lon': 0.0}  
anomaly_message = ""  

# Function to periodically fetch vessel data
def fetch_vessel_data(mmsi, api_key, weather_api_key):  
    global anomaly_message  
    while True:
        params = {
            'api-key': api_key,
            'mmsi': mmsi
        }
        api_base = ''
        method = 'vessel'

        # Fetch vessel data from the API
        response = requests.get(api_base + method, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                vessel_info = data['data']
                speed = vessel_info.get('speed', 0)  
                course = vessel_info.get('course', 0)  
                lat = vessel_info.get('lat', 0.0)  
                lon = vessel_info.get('lon', 0.0)  

               
                ship_speed.append(speed)
                ship_course.append(course)
                ship_position['lat'] = lat
                ship_position['lon'] = lon

                # Check for anomalies in speed and course
                if speed > 20:  
                    anomaly_message = "Anomaly Detected: Speed exceeds normal threshold!"
                elif len(ship_course) > 1 and abs(ship_course[-1] - ship_course[-2]) > 30:  
                    anomaly_message = "Anomaly Detected: Sudden large change in course detected!"
                elif speed < 2 and 'clear' in get_weather_data(lat, lon, weather_api_key)['description'].lower():
                    
                    anomaly_message = "Anomaly Detected: Slow movement despite good weather conditions!"
                else:
                    anomaly_message = "No anomalies detected. Vessel is operating normally."

                print(anomaly_message)  
            else:
                print("No vessel data found.")
        else:
            print('Failed to fetch data. Please check the API and MMSI.')

        time.sleep(60)  

# Function to fetch weather data
def get_weather_data(lat, lon, weather_api_key):
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={weather_api_key}"
    response = requests.get(weather_url)
    if response.status_code == 200:
        data = response.json()
        weather_info = {
            'temp': data['main']['temp'],
            'description': data['weather'][0]['description'],
            'wind_speed': data['wind']['speed']
        }
        return weather_info
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    global anomaly_message  
    vessel_info = None
    speed_plot_url = ""
    course_plot_url = ""
    weather_info = None

    if request.method == 'POST':
        mmsi = request.form.get('mmsi')
        api_key = ''  # Replace with your actual API key
        weather_api_key = ''  # Replace with your actual weather API key

     
        threading.Thread(target=fetch_vessel_data, args=(mmsi, api_key, weather_api_key), daemon=True).start()  

        params = {
            'api-key': api_key,
            'mmsi': mmsi
        }
        api_base = 'https://api.datalastic.com/api/v0/'
        method = 'vessel'


        response = requests.get(api_base + method, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                vessel_info = data['data']
                lat = vessel_info['lat']
                lon = vessel_info['lon']

                speed_plot_url = generate_speed_plot(ship_speed)
                course_plot_url = generate_course_plot(ship_course)

                weather_info = get_weather_data(lat, lon, weather_api_key)
            else:
                vessel_info = {'error': 'No vessel data found for the given MMSI.'}
        else:
            vessel_info = {'error': 'Failed to fetch data. Please try again.'}

    return render_template('index.html', vessel_info=vessel_info, speed_plot_url=speed_plot_url,
                           course_plot_url=course_plot_url, weather_info=weather_info, anomaly_message=anomaly_message)

@app.route('/position', methods=['GET'])
def get_position():
    return jsonify(ship_position)

def generate_speed_plot(speed_data):
   
    plt.figure()
    plt.plot(speed_data, marker='o')
    plt.title('Ship Speed Visualization')
    plt.xlabel('Time (arbitrary units)')
    plt.ylabel('Speed (knots)')
    plt.grid(True)


    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img = base64.b64encode(buf.getvalue()).decode('utf8')
    plt.close()

    return f'data:image/png;base64,{img}'

def generate_course_plot(course_data):
    
    plt.figure()
    plt.plot(course_data, marker='o')
    plt.title('Ship Course Visualization')
    plt.xlabel('Time (arbitrary units)')
    plt.ylabel('Course (degrees)')
    plt.grid(True)

   
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img = base64.b64encode(buf.getvalue()).decode('utf8')
    plt.close()

    return f'data:image/png;base64,{img}'

if __name__ == '__main__':
    app.run(debug=True)
