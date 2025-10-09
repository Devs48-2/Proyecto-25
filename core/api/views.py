from rest_framework import viewsets, status
from rest_framework.response import Response

from .serializers import QuestionSerializer
from core.utils import human_query_to_sql, execute_sql_query, build_answer

import json
class QuestionViewSet(viewsets.GenericViewSet):
    serializer_class = QuestionSerializer
    """
    A simple ViewSet for handling questions.
    """
    
    def create(self, request):
        serializer = QuestionSerializer(data=request.data)
        data = {}
        print(request.data)
        if serializer.is_valid():
            question = serializer.validated_data['question']
            response = human_query_to_sql(question)
            print(response)
            try:
                context = json.loads(response)
                sql_query = context.get('sql_query', '')
                description = context.get('description', '')
                print(sql_query)
                data['question'] = question
                if sql_query:
                    result = execute_sql_query(sql_query)
                    answer = build_answer(result, question)
                    data['status'] = 'ok'
                    data['answer'] = answer
                elif description:
                    data['status'] = 'ok'
                    data['answer'] = description
                else:
                    data['status'] = 'error'
                    data['answer'] = 'Lo siento, no lo sé'
            except json.JSONDecodeError:
                data['status'] = 'error'
                data['answer'] = 'Error al procesar la respuesta del modelo'

            print(data)

            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)