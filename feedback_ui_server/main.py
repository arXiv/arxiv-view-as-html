from flask import Flask, render_template, redirect
app = Flask(__name__, 
            static_folder='../ConversionContainer/bucket_static', 
            template_folder='.')

@app.route('/', methods=['GET'])
def main ():
    return redirect('2012.02201v1/2012.02201v1.html')

@app.route('/2012.02201v1/2012.02201v1.html')
def paper ():
    return render_template('sample_paper.html')

if __name__ == '__main__':
    app.run('127.0.0.1', 8000, True)