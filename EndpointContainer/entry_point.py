from factory import create_web_app

app = create_web_app()

if __name__=='__main__':
    app.run(debug=False)