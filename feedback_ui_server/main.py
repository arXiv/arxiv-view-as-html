from flask import Flask, render_template

app = Flask(__name__, 
            static_folder='../ConversionContainer/bucket_static', 
            template_folder='.')

@app.route('/', methods=['GET'])
def main ():
    return render_template('sample_paper.html')

if __name__ == '__main__':
    app.run('127.0.0.1', 8000, True)