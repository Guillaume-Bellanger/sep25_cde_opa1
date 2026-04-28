from pymongo import MongoClient
from pymongo.database import Database
import logging
import sqlalchemy
from typing import TypedDict
from sqlalchemy.engine import Engine
import pandas as pd
import datetime

logger = logging.getLogger("CRYPTO_BOT")


def connect_to_postgres(db_name: str, user: str, password: str, host: str = "localhost", port: int = 5432) -> Engine:
  """
  Connect to a PostgreSQL database and return the SQLAlchemy engine.

  Args:
      db_name (str): Name of the database.
      user (str): Database user.
      password (str): Database password.
      host (str, optional): Database host. Defaults to “localhost”.
      port (int, optional): Database port. Defaults to 5432.

  Returns:
      Engine: SQLAlchemy engine connected to the PostgreSQL database.
  """
  try:
    engine = sqlalchemy.create_engine(
      f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}",
      connect_args={"connect_timeout": 5},
    )
    logger.info(f"Connected to PostgreSQL database: {db_name} at {host}:{port} as user {user}")
    return engine
  except Exception as e:
    logger.error(f"Error connecting to PostgreSQL: {e}")
    raise


def connect_to_mongo(db_name: str, host: str, port: int = 27017, auth: bool = True, user: str = "",
                     password: str = "") -> MongoClient:
  """
  Connect to a MongoDB database and return the client.

  Args:
      db_name (str): Name of the database.
      host (str): MongoDB server address.
      port (int, optional): MongoDB server port. Defaults to 27017.
      auth (bool, optional): Whether authentication is required. Defaults to True.
      user (str): Database user.
      password (str): Database password.

  Returns:
      MongoClient: Mongo client.
  """
  try:
    uri = "mongodb://{}:{}@{}:{}/".format(user, password, host,
                                          port) if auth else "mongodb://{}:{}/".format(host, port)
    client = MongoClient(uri)
    logger.info(f"Connected to MongoDB database: {db_name}")
    return client
  except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    raise


def write_to_mongo(db_name: str, collection_name: str, data: list[dict]) -> None:
  """
  Write data to a MongoDB collection.

  Args:
      db_name (str): Name of the database.
      collection_name (str): Name of the collection.
      data (list[dict]): List of data to insert.
  """
  try:
    client = MongoClient("mongodb://localhost:27017/")
    db: Database = client[db_name]
    collection = db[collection_name]
    if data:
      collection.insert_many(data)
      logger.info(f"Inserted {len(data)} records into {db_name}.{collection_name}")
    else:
      logger.warning("No data provided to insert.")
    client.close()
  except Exception as e:
    logger.error(f"Error writing to MongoDB: {e}")


def write_to_postgres(engine: Engine, table_name: str, data: list[TypedDict]) -> None:
  """
  Write data to a PostgreSQL table.

  Args:
      engine (Engine): SQLAlchemy engine connected to the PostgreSQL database.
      table_name (str): Name of the table.
      data (list[TypedDict]): List of data to insert.
  """
  if not data:
    logger.warning("No data provided to insert.")
    return

  try:
    with engine.connect() as connection:
      metadata = sqlalchemy.MetaData()
      table = sqlalchemy.Table(table_name, metadata, autoload_with=engine)
      insert_stmt = table.insert().values(data)
      connection.execute(insert_stmt)
      logger.info(f"Inserted {len(data)} records into {table_name}")
  except Exception as e:
    logger.error(f"Error writing to PostgreSQL: {e}")


def read_from_postgres(engine: Engine, query: str) -> list[dict]:
  """
  Read data from a PostgreSQL database.

  Args:
      engine (Engine): SQLAlchemy engine connected to the PostgreSQL database.
      query (str): SQL query to execute.

  Returns:
      list[TypedDict]: List of records retrieved from the database.
  """
  try:
    with engine.connect() as connection:
      result = connection.execute(sqlalchemy.text(query))
      records = [dict(row) for row in result]
      logger.info(f"Retrieved {len(records)} records from PostgreSQL")
      return records
  except Exception as e:
    logger.error(f"Error reading from PostgreSQL: {e}")
    return []


def read_from_mongo(db: Database, collection_name: str, query=None) -> pd.DataFrame:
  """
  Read data from a MongoDB collection.

  Args:
      db (str): Name of the database.
      collection_name (str): Name of the collection.
      query (dict, optional): Query to filter documents. Defaults to None.

  Returns:
      pd.DataFrame: DataFrame containing the retrieved documents.
  """
  if query is None:
    query = {}
  try:
    count = db[collection_name].count_documents(query)
    logger.debug(f"(MONGO) {collection_name} COUNT {count} DOCUMENTS")

    df = pd.DataFrame()

    # We read in steps to avoid memory issues
    step = 10000
    for i in range(0, int(count / step) + 1):
      logger.debug(f"(MONGO) STEP BETWEEN {step * i} and {step * (i + 1)} ")

      finds = db[collection_name].find(query).skip(i * step).limit(step)
      tmp = pd.DataFrame.from_dict(finds)
      tmp = convert_date(tmp).copy()

      df = pd.concat([df, tmp], ignore_index=True)

    logger.info(f"Retrieved {df.shape[0]} documents from {db}.{collection_name}")
    return df
  except Exception as e:
    logger.error(f"Error reading from MongoDB: {e}")
    return pd.DataFrame()


def convert_date(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
  """
  Convertit les dates en UTC et les objets pouvant être des dates en string
  :param df: Dataframe analysé
  :param inplace: True signifie que le DataFrame en paramètre sera directement modifié
  :return: Dataframe modifié
  """
  df_transform = df.copy()
  if inplace:
    df_transform = df

  columns = df_transform.select_dtypes(include=["object"]).columns.tolist()
  for column in columns:
    if df_transform[column].shape[0] > 0 and type(df_transform[column].iloc[0]) is datetime.date:
      df_transform[column] = pd.to_datetime(df_transform[column], utc=True)

  columns = df_transform.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns.tolist()
  for column in columns:
    df_transform[column] = pd.to_datetime(df_transform[column], utc=True)

  return df_transform
