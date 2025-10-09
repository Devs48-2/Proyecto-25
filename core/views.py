import json
from django.shortcuts import render

from .utils import get_schema, human_query_to_sql, execute_sql_query, build_answer
from .forms import QuestionForm
def home(request):
    schema_database = get_schema()

    data = {
        'form': QuestionForm(),
    }

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            data['form'] = form

            question = form.cleaned_data['question']
            response = human_query_to_sql(question)
            print(response)
            try:
                context = json.loads(response)
                sql_query = context.get('sql_query', '')
                description = context.get('description', '')
                print(sql_query)
                if sql_query:
                    result = execute_sql_query(sql_query)
                    print(result)
                    answer = build_answer(result, question)
                    print(answer)
                    data['answer'] = answer
                elif description:
                    data['answer'] = description
                else:
                    data['answer'] = 'Lo siento, no lo sé'

            except json.JSONDecodeError:
                context = {'sql_query': response}

    return render(request, 'home.html', data)