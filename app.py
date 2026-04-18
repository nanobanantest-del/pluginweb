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
    # Naye form se saara data lena
    plugin_name = request.form.get('plugin_name').replace(" ", "")
    package_name = request.form.get('package_name')
    main_class = request.form.get('main_class') # Ab main class ka naam exact pata hoga
    api_type = request.form.get('api_type')
    api_version = request.form.get('api_version')
    java_version = request.form.get('java_version')
    plugin_yml_content = request.form.get('plugin_yml_content') # Universal YAML
    java_files = request.files.getlist('java_files')

    if not plugin_name or not package_name or not java_files or not main_class:
        return "Missing important details!", 400

    job_id = str(uuid.uuid4())[:8]
    base_dir = os.path.join(BUILD_DIR, f"{plugin_name}_{job_id}")
    
    java_dir = os.path.join(base_dir, "src", "main", "java", *package_name.split('.'))
    resources_dir = os.path.join(base_dir, "src", "main", "resources")
    os.makedirs(java_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # .java files save karna (Multiple files support)
    for file in java_files:
        if file.filename.endswith('.java'):
            file.save(os.path.join(java_dir, file.filename))

    # Spigot aur Paper ke liye alag Maven repo logic
    if api_type == "paper":
        repo_id, repo_url = "papermc", "https://repo.papermc.io/repository/maven-public/"
        dep_group, dep_artifact = "io.papermc.paper", "paper-api"
    else:
        repo_id, repo_url = "spigot-repo", "https://hub.spigotmc.org/nexus/content/repositories/snapshots/"
        dep_group, dep_artifact = "org.spigotmc", "spigot-api"

    # Universal pom.xml generate karna
    pom_content = f"""<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
      <modelVersion>4.0.0</modelVersion>
      <groupId>{package_name}</groupId>
      <artifactId>{plugin_name}</artifactId>
      <version>1.0</version>
      
      <properties>
          <maven.compiler.source>{java_version}</maven.compiler.source>
          <maven.compiler.target>{java_version}</maven.compiler.target>
          <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
      </properties>

      <repositories>
          <repository>
              <id>{repo_id}</id>
              <url>{repo_url}</url>
          </repository>
      </repositories>
      <dependencies>
          <dependency>
              <groupId>{dep_group}</groupId>
              <artifactId>{dep_artifact}</artifactId>
              <version>{api_version}-R0.1-SNAPSHOT</version>
              <scope>provided</scope>
          </dependency>
      </dependencies>
    </project>"""
    
    with open(os.path.join(base_dir, "pom.xml"), "w") as f:
        f.write(pom_content)

    # Universal plugin.yml save karna (Direct UI se aaya hua)
    with open(os.path.join(resources_dir, "plugin.yml"), "w") as f:
        f.write(plugin_yml_content)

    # Compile karna
    try:
        subprocess.run(["mvn", "clean", "package"], cwd=base_dir, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(base_dir)
        error_msg = e.stdout.decode() + "\n" + e.stderr.decode()
        return f"<h3 style='color:white; font-family:sans-serif;'>Compilation Failed! Error details:</h3><pre style='background:#1e1e1e; color:#ff5555; padding:15px; border-radius:8px; overflow-x:auto;'>{error_msg}</pre>", 500

    # .jar file return karna
    target_dir = os.path.join(base_dir, "target")
    jar_file = None
    for file in os.listdir(target_dir):
        if file.endswith(".jar") and not file.startswith("original"):
            jar_file = os.path.join(target_dir, file)
            break

    if jar_file:
        return send_file(jar_file, as_attachment=True)
    else:
        return "Jar file compile nahi ho payi.", 500

if __name__ == '__main__':
    os.makedirs(BUILD_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=80)
