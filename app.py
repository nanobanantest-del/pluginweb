import os
import shutil
import subprocess
import uuid
from flask import Flask, request, render_template, send_file

app = Flask(__name__)
app.secret_key = "super_secret_key"
BUILD_DIR = "builds"

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/compile', methods=['POST'])
def compile_plugin():
    # Form se data lena
    plugin_name = request.form.get('plugin_name').replace(" ", "")
    package_name = request.form.get('package_name')
    api_version = request.form.get('api_version')
    java_files = request.files.getlist('java_files')

    if not plugin_name or not package_name or not java_files:
        return "Missing details!", 400

    # Ek unique folder ID banana taki alag-alag builds mix na hon
    job_id = str(uuid.uuid4())[:8]
    base_dir = os.path.join(BUILD_DIR, f"{plugin_name}_{job_id}")
    
    # Maven ka standard folder structure banana
    java_dir = os.path.join(base_dir, "src", "main", "java", *package_name.split('.'))
    resources_dir = os.path.join(base_dir, "src", "main", "resources")
    os.makedirs(java_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # Upload hui .java files ko sahi jagah save karna
    for file in java_files:
        if file.filename.endswith('.java'):
            file.save(os.path.join(java_dir, file.filename))

    # pom.xml file generate karna
    pom_content = f"""<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
      <modelVersion>4.0.0</modelVersion>
      <groupId>{package_name}</groupId>
      <artifactId>{plugin_name}</artifactId>
      <version>1.0</version>
      <repositories>
          <repository>
              <id>papermc</id>
              <url>https://repo.papermc.io/repository/maven-public/</url>
          </repository>
      </repositories>
      <dependencies>
          <dependency>
              <groupId>io.papermc.paper</groupId>
              <artifactId>paper-api</artifactId>
              <version>{api_version}-R0.1-SNAPSHOT</version>
              <scope>provided</scope>
          </dependency>
      </dependencies>
    </project>"""
    with open(os.path.join(base_dir, "pom.xml"), "w") as f:
        f.write(pom_content)

    # plugin.yml file generate karna
    main_class = [f.filename[:-5] for f in java_files if f.filename.endswith('.java')][0] 
    plugin_yml_content = f"name: {plugin_name}\nversion: 1.0\nmain: {package_name}.{main_class}\napi-version: '{api_version.rsplit('.', 1)[0]}'\n"
    with open(os.path.join(resources_dir, "plugin.yml"), "w") as f:
        f.write(plugin_yml_content)

    # Maven Build Command run karna
    try:
        subprocess.run(["mvn", "clean", "package"], cwd=base_dir, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(base_dir) # Agar compile fail ho toh kachra delete kar do
        return f"<h3>Compilation Failed! Code mein error hai:</h3><pre style='background:#1e1e1e; color:red; padding:10px;'>{e.stderr.decode()}</pre>", 500

    # target folder se ban chuki .jar file uthana
    target_dir = os.path.join(base_dir, "target")
    jar_file = None
    for file in os.listdir(target_dir):
        if file.endswith(".jar") and not file.startswith("original"):
            jar_file = os.path.join(target_dir, file)
            break

    # Plugin successfully ban gaya, ab direct download karwa do
    if jar_file:
        return send_file(jar_file, as_attachment=True)
    else:
        return "Jar file compile nahi ho payi.", 500

if __name__ == '__main__':
    os.makedirs(BUILD_DIR, exist_ok=True)
    # Direct port 80 par public IP ke sath run karna
    app.run(host='0.0.0.0', port=80)
