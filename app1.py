
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import mysql.connector
import re

app = Flask(__name__)

# MySQL configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'entity'
}

chrome_options = Options()
chrome_options.add_argument("--headless")
webdriver_service = Service('D:/downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe')

def get_selenium_driver():
    return webdriver.Chrome(service=webdriver_service, options=chrome_options)

def extract_entities_from_text(text):

    artists = []
    programs = []
    date_time = ""

    ######################so we are Extract artists and roles
    artist_section = re.findall(r'Artists\s*([\s\S]*?)\nPROGRAM', text, re.IGNORECASE)
    if artist_section:
        artist_lines = artist_section[0].strip().split('\n')
        for i in range(0, len(artist_lines), 2):
            if i + 1 < len(artist_lines):
                artist_name = artist_lines[i].strip()
                artist_role = artist_lines[i + 1].strip()
                artists.append({
                    "artist_name": artist_name,
                    "artist_role": artist_role
                })

    #
    program_section = re.findall(r'PROGRAM\s*([\s\S]*?)\nDIGITAL PROGRAM BOOK', text, re.IGNORECASE)
    if program_section:
        program_lines = program_section[0].strip().split('\n')
        programs = [line.strip() for line in program_lines if line.strip()]

    ############# Extract date and time
    date_time_section = re.findall(r'performances\s*([\s\S]*?)\nTickets', text, re.IGNORECASE)
    if date_time_section:
        date_time = date_time_section[0].strip()

    ################# Combine data
    entities = []
    for artist in artists:
        entities.append({
            "artist_name": artist["artist_name"],
            "artist_role": artist["artist_role"],
            "programs": programs,
            "date_time": date_time
        })

    return entities

@app.route('/api/save-entity', methods=['GET'])
def save_entity():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400

    driver = get_selenium_driver()
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//body"))
        )

        ################ Extract text from the entire webpage
        elements = driver.find_elements(By.XPATH, "//*")
        text = ' '.join([element.text for element in elements if element.text])
        print("Extracted text from webpage:\n", text)  # Debugging line

        # Extract entities
        entities = extract_entities_from_text(text)
        print("Extracted entities:", entities)  # Debugging line

        if not entities:
            print("No entities extracted to insert")  # Debugging line
            return jsonify({'message': 'No entities found to save'}), 200

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()


        cursor.execute("DROP TABLE IF EXISTS EntitiesMaster")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS EntitiesMaster (
            id INT AUTO_INCREMENT PRIMARY KEY,
            artist_name VARCHAR(255),
            artist_role VARCHAR(255),
            programs TEXT,
            date_time VARCHAR(255),
            url TEXT
        )
        """)
        print("Table creation or check completed")

        print("Inserting entities into database")

        for entity in entities:
            cursor.execute("""
            INSERT INTO EntitiesMaster (artist_name, artist_role, programs, date_time, url)
            VALUES (%s, %s, %s, %s, %s)
            """, (entity['artist_name'], entity['artist_role'], ', '.join(entity['programs']), entity['date_time'], url))
            print("SQL Query Executed:", cursor.statement)

        conn.commit()
        print("Data committed to database")
        cursor.close()
        conn.close()
        driver.quit()

        return jsonify({'message': 'Entities saved successfully'}), 200

    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        return jsonify({'error': str(err)}), 500
    except Exception as e:
        print("Error:", str(e))  # Debugging line
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-entity', methods=['GET'])
def get_entity():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL parameter is required'}), 400

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT * FROM EntitiesMaster WHERE url = %s
    """, (url,))

    entities = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify(entities), 200

if __name__ == '__main__':
    app.run(debug=True)


