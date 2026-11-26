class Config:
    JWT_ALGORITHM = "HS256"
    # shared settings go here

class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE = "recipes-dev.db"

class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    DATABASE = "recipes-test.db"

class ProductionConfig(Config):
    DEBUG = False
    DATABASE = "recipes.db"
