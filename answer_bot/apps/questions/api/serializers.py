# serializers.py
from rest_framework import serializers
from apps.questions.models import ImprovedResponse

class MCQSerializer(serializers.ModelSerializer):
    qid         = serializers.IntegerField(required=True)
    question    = serializers.CharField(required=True)
    op1         = serializers.CharField(required=True, source='opa')
    op2         = serializers.CharField(required=True, source='opb')
    op3         = serializers.CharField(required=True, source='opc')
    op4         = serializers.CharField(required=True, source='opd')
    cop         = serializers.CharField(required=True, source='correct_answer')
    expm        = serializers.CharField(required=True, source='explanation')
    type        = serializers.IntegerField(required=True)

    new_question    = serializers.CharField(read_only=True, source='improved_question')
    new_op1         = serializers.CharField(read_only=True, source='improved_opa')
    new_op2         = serializers.CharField(read_only=True, source='improved_opb')
    new_op3         = serializers.CharField(read_only=True, source='improved_opc')
    new_op4         = serializers.CharField(read_only=True, source='improved_opd')
    new_cop         = serializers.CharField(read_only=True, source='correct_answer')
    new_expm        = serializers.CharField(read_only=True, source='improved_explanation')

    class Meta:
        model = ImprovedResponse
        fields = [
            'qid','question','op1','op2','op3','op4',
            'cop','expm','type','new_cop',
            'gpt_explanation','new_question', 'new_op1',
            'new_op2','new_op3', 'new_op4',
            'new_expm','flag_for_human_review'
        ]

        read_only_fields = [
            'new_cop', 'gpt_explanation',
            'new_question', 'new_op1', 'new_op2',
            'new_op3', 'new_op4', 'new_expm',
            'flag_for_human_review','type'
        ]

    def create(self, validated_data):
        return ImprovedResponse.objects.create(**validated_data)
    

class MCQSearchResultSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model = ImprovedResponse
        fields = [
            'id', 'question', 'options', 'correct_answer', 'explanation'
        ]

    def get_options(self, obj):
        return {
            "A": obj.opa,
            "B": obj.opb,
            "C": obj.opc,
            "D": obj.opd
        }

