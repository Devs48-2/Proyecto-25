from django import forms

class QuestionForm(forms.Form):
    question = forms.CharField(label='Pregunta', max_length=1000)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Escribe tu pregunta aquí...',
            'rows': 3,
            'style': 'width: 100%;',
            'autocomplete': 'off'
        })