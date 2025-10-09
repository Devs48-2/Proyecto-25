from rest_framework import serializers

class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=1000, required=True)
    answer = serializers.CharField(max_length=1000, required=False, allow_blank=True)