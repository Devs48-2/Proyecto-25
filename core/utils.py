from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

import json
import openai

load_dotenv()
# Create your views here.

DB = 'sqlite:///C:/Users/Cristhian Zapata/Documents/crm1/CRM/db_1.sqlite3'
DB_POSTGRESQL = f"postgresql+psycopg2://postgres:123456789@localhost:5432/hoorass48"

def get_schema():
    engine = create_engine(DB_POSTGRESQL)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    def get_column_details(table_name):
        columns = inspector.get_columns(table_name)
        return [f'{column["name"]} ({column["type"]})' for column in columns]
    
    schema_info = []
    for table_name in table_names:
        table_info = [f"Table: {table_name}"]
        table_info.append('Columns')
        table_info.extend(f' - {col}' for col in get_column_details(table_name))
        schema_info.append('\n'.join(table_info))
    
    engine.dispose()  # Close the connection
    return '\n\n'.join(schema_info)

def human_query_to_sql(human_query):
    database_schema = get_schema()

    system_message = f"""
        Given the following schema, write a SQL query in POSTGRESQL that retrieves the requested information. 
        Return the SQL query inside a JSON structure with the key "sql_query". and quit the word json of the response.

        INSTRUCCIONES ESPECÍFICAS:
        1. Si la tabla no existe, puede ser que el cliente quiera preguntar algo de asistencia en viajes en ese caso respondemos igual con un json en un campo "description" e investigas el tema y nos das una respuesta con un experto en asistencia en viajes.

        2. Si preguntan por planes y te dicen a donde quieren viajar, puedes buscar en la tabla de planes y responder con un json que contenga el campo "sql_query" con la consulta a la tabla de planes teniendo en cuenta el campo destino es una llave foranea de la tabal country_destination y ahi buscar por el name Worldwide.

        3. Recuerda la estructura de PostgreSQL, por ejemplo, si el campo de la tabla es camelCase, debes agregarlo en comillas dobles ya que sino lo haces PostgreSQL pasa el campo a todo minuscula y va generar error en la consulta, un ejemplo de esto es SELECT id FROM paises_paises WHERE "nomPais" = "España"

        4. Si te preguntan por algo como Preguntas de programacion, preguntas de matemáticas. debes responder con un json que contenga el campo "description" y una respuesta que diga, Lo siento, no lo sé.

        Las opciones 1,2,3 y 4 son ultima opcion, debes intentar siempre responder con una consulta SQL.

        <example>{{
            "sql_query": "SELECT * FROM users WHERE age > 18;"
            "original_query": "Show me all users older than 18 years old."
        }}
        </example>
        <schema>
        {database_schema}
        </schema>
    """
    user_message = human_query

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        response_format={
            "type": "json_object",
        },
        # max_tokens=4000,
    )
    
    return response.choices[0].message.content.strip() if response.choices else "No response from model"

def execute_sql_query(sql_query):

    sql_lower = sql_query.strip().lower()
    if sql_lower.startswith("delete") or sql_lower.startswith("update"):
        return "Operación no permitida: no se puede ejecutar DELETE o UPDATE."


    engine = create_engine(DB_POSTGRESQL)

    with engine.connect() as connection:
        result = connection.execute(text(sql_query))
        try:
            rows = result.fetchall()
            if not rows:
                return "La consulta no devolvió filas."
            return rows
        except Exception:
            return "La consulta se ejecutó pero no devolvió filas (posiblemente no es una SELECT)."
    
def build_answer(result, human_query):
    system_message = f"""
        Given a users question and the SQL rows response from the database from which the user wants to get the answer,
        write a response to the user's question.
        <user_question> 
        {human_query}
        </user_question>
        <sql_response>
        ${result} 
        </sql_response>
    """

    response = ChatOpenAI(model="gpt-4o-mini").invoke([SystemMessage(content=system_message)])
    return response.content