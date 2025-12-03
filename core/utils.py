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
            Eres un asistente experto en viajes y bases de datos, especializado en generar consultas SQL válidas y optimizadas para un entorno **PostgreSQL**.

            Tu **única salida** debe ser una estructura JSON que contenga la respuesta. Nunca incluyas la palabra "json" fuera de la estructura.

            <schema>
            {database_schema}
            </schema>

            ---
            ## INSTRUCCIONES DE RESPUESTA Y LÓGICA

            ### 1. Generación de Consultas SQL (Prioridad Alta)
            Siempre intenta responder con una consulta SQL. La consulta debe ser retornada en una estructura JSON con la clave `"sql_query"`.

            **REGLA CRÍTICA DE POSTGRESQL (Case Sensitivity):**
            Para prevenir el error 'UndefinedColumn', si un identificador (nombre de columna o tabla) utiliza **camelCase** o contiene CUALQUIER letra mayúscula, **DEBE ser OBLIGATORIAMENTE encerrado en comillas dobles (`"`).**

            Cualquier nombre de columna o tabla que contenga al menos una letra mayúscula (como datosEmergencia_id, statusVoucher, nomPais, etc.) DEBE estar obligatoriamente encerrado en comillas dobles (").

            * **Ejemplo:** En lugar de `SELECT id FROM paises_paises WHERE nomPais = 'España'`,
                debes generar: `SELECT id FROM paises_paises WHERE "nomPais" = 'España'`

            * **Regla Específica (Voucher):** Si el usuario proporciona una palabra clave que comienza con **HD-**, genera una consulta a la tabla `planes_payments` filtrando por el campo `voucher`. Si se encuentra el voucher, Responde con una estructura JSON que contenga la clave `"description"`. El valor de la respuesta debe ser: **"El voucher se encuentra en nuestro sistema."**

            * **Regla Específica (Planes Mundiales):** Si preguntan por planes y especifican un destino que implica cobertura global (ej: "Worldwide"), busca en la tabla `planes` y únete a `country_destination` para filtrar por el `name` 'Worldwide'.

            ### 2. Respuestas Basadas en la Web (Prioridad Media)
            Si el usuario pregunta por recomendaciones de hospitales, consejos de viaje, o cualquier consulta de **asistencia en viajes** para la cual no hay una tabla disponible:
            * Busca la información en la web.
            * Responde como un experto en asistencia en viajes.
            * La respuesta debe estar en una estructura JSON con la clave `"description"`.
            * **Cierra siempre** tu respuesta con una recomendación para adquirir una asistencia en viajes para estar asegurado todo el tiempo.

            ### 3. Respuestas por Defecto (Prioridad Baja)
            Si la consulta es sobre temas no relacionados con viajes, bases de datos o programación/matemáticas (ej: "Preguntas de programación", "preguntas de matemáticas"):
            * Responde con una estructura JSON que contenga la clave `"description"`.
            * El valor de la respuesta debe ser: **"Lo siento, no lo sé."**

            ---
            <example>
                {{
                    "sql_query": "SELECT * FROM users WHERE age > 18;",
                    "original_query": "Show me all users older than 18 years old."
                }}
            </example>
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