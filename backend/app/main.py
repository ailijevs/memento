from fastapi import FastAPI


app = FastAPI()

@app.get("/")
def hello() -> str:
    return "Hello world, welcome to Memento"
