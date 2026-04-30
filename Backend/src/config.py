from dotenv import load_dotenv
import os
load_dotenv()


class Config:
    
    SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
    SPOONACULAR_URL_BASE = os.getenv("SPOONACULAR_URL_BASE")