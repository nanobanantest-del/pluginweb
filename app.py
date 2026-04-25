import os
import subprocess
import shutil
from flask import Flask, request, render_template, send_file

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compile', methods=['POST'])
def compile_plugin():
    # 1. Purane build ko clean karo
    build_dir = "build_workspace"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    # Package path banaiye (me.akash.practicebots)
    java_src_dir = os.path.join(build_dir, "src", "main", "java", "me", "akash", "practicebots")
    resources_dir = os.path.join(build_dir, "src", "main", "resources")
    os.makedirs(java_src_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # 2. Upload hui saari .java files ko save karo
    java_files = request.files.getlist('java_files')
    for f in java_files:
        if f and f.filename:
            f.save(os.path.join(java_src_dir, f.filename))

    # 3. Upload hui plugin.yml ko save karo
    plugin_yml = request.files.get('plugin_yml')
    if plugin_yml and plugin_yml.filename:
        plugin_yml.save(os.path.join(resources_dir, "plugin.yml"))

    # 4. Custom Maven Dependencies Box ka data receive karo
    custom_pom_data = request.form.get('pom_extras', '')

    # 5. Dynamic pom.xml generate karo
    pom_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>me.akash.practicebots</groupId>
    <artifactId>PracticeBots</artifactId>
    <version>FINAL-RELEASE</version>

    <properties>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <repositories>
        <repository>
            <id>papermc-repo</id>
            <url>https://repo.papermc.io/repository/maven-public/</url>
        </repository>
    </repositories>

    <dependencies>
        <dependency>
            <groupId>io.papermc.paper</groupId>
            <artifactId>paper-api</artifactId>
            <version>1.19.4-R0.1-SNAPSHOT</version>
            <scope>provided</scope>
        </dependency>
    </dependencies>

    {custom_pom_data}

</project>
"""
    # pom.xml ko file me save karo
    with open(os.path.join(build_dir, "pom.xml"), "w", encoding="utf-8") as f:
        f.write(pom_content)

    # 6. Maven Compile Command Run karo
    try:
        process = subprocess.Popen(
            ["mvn", "clean", "package"], 
            cwd=build_dir, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True
        )
        output, _ = process.communicate()

        # Agar success hua toh .jar file download ke liye bhejo
        if process.returncode == 0:
            target_dir = os.path.join(build_dir, "target")
            jar_path = None
            if os.path.exists(target_dir):
                for file in os.listdir(target_dir):
                    if file.endswith(".jar") and not file.startswith("original-"):
                        jar_path = os.path.join(target_dir, file)
                        break
            
            if jar_path:
                return send_file(jar_path, as_attachment=True)
            else:
                return f"<h2 style='color:green;'>BUILD SUCCESS!</h2><p>Lekin JAR file nahi mili.</p><pre>{output}</pre>"
        else:
            return f"<h2 style='color:red;'>BUILD FAILED!</h2><pre>{output}</pre>"

    except Exception as e:
        return f"<h2 style='color:red;'>COMPILER ERROR!</h2><pre>{str(e)}</pre>"

if __name__ == '__main__':
    # GitHub Codespaces par run karne ke liye 0.0.0.0 zaruri hai
    app.run(host='0.0.0.0', port=8080, debug=True)
            
