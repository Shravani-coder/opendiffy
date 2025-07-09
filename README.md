1. Start MongoDB

Open two separate terminals:

Terminal 1: Start the MongoDB server:

mongod --dbpath /path/to/your/data/db

Terminal 2: Open the MongoDB shell:

mongosh

2. Build Diffy

In a new terminal, navigate to your Diffy project root:

cd /path/to/odiffy
mvn clean package -DskipTests

This will generate target/diffy.jar.

3. Run the Diffy JAR

Still in the project root, start Diffy:

java -jar target/diffy.jar



4. Start Mock Servers

Diffy will forward requests to three endpoints. You can use Python’s simple HTTP server.

Primary service (port 9100):

cd odiffy/static/primary
python3 -m http.server 9100

Secondary service (port 9200):

cd odiffy/static/secondary
python3 -m http.server 9200

Candidate service (port 9000):

cd odiffy/static/candidate
python3 -m http.server 9100

5. Sending Test Requests

In another terminal, go back to the project root and run:

cd /path/to/odiffy
python3 send_requests.py

This script will fire requests through Diffy and display comparison results.