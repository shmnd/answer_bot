# serializers.py
from rest_framework import serializers
from apps.questions.models import ImprovedResponse

class MCQSerializer(serializers.ModelSerializer):
    question = serializers.CharField(required=True)
    opa = serializers.CharField(required=True)
    opb = serializers.CharField(required=True)
    opc = serializers.CharField(required=True)
    opd = serializers.CharField(required=True)
    correct_answer = serializers.CharField(required=True)
    explanation = serializers.CharField(required=True)

    class Meta:
        model = ImprovedResponse
        fields = [
                'question','opa','opb','opc','opd','correct_answer',
                'explanation','gpt_answer', 'gpt_explanation',
                'improved_question', 'improved_opa', 'improved_opb',
                'improved_opc', 'improved_opd', 'improved_explanation'
            ]

        read_only_fields = [
            'gpt_answer', 'gpt_explanation',
            'improved_question', 'improved_opa', 'improved_opb',
            'improved_opc', 'improved_opd', 'improved_explanation'
        ]

        extra_kwargs = {
            'question': {'required': True},
            'opa': {'required': True},
            'opb': {'required': True},
            'opc': {'required': True},
            'opd': {'required': True},
            'correct_answer': {'required': True},
            'explanation': {'required': True},
        }

    def create(self, validated_data):
        return ImprovedResponse.objects.create(**validated_data)
