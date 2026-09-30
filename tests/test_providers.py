import io
import json
from unittest.mock import patch
from django.test import SimpleTestCase,override_settings
from apps.assistente.providers import converse,ProviderFailure

@override_settings(OPENAI_API_KEY='test-only',OPENAI_TEXT_MODEL='test-model')
class TextProviderContractTests(SimpleTestCase):
    def response(self,quote='Cria site'):
        return {'status':'completed','model':'test-model','usage':{'input_tokens':80,'output_tokens':20},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'message':'Consulte a skill fornecida.','citations':[{'id':'project:node','quote':quote}]})}]}]}

    def context(self):
        return {'results':[{'id':'node','project_id':'project','name':'Site','project':'Example','kind':'skill','excerpt':'Cria site com frontend.'}],'history':[],'history_partial':False}

    def test_wire_contract_and_no_tools(self):
        with patch('urllib.request.build_opener') as transport:
            transport.return_value.open.return_value=io.BytesIO(json.dumps(self.response()).encode())
            result=converse('Criar site',self.context())
            request=transport.return_value.open.call_args.args[0]
            payload=json.loads(request.data)
            self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
            self.assertFalse(payload['store']);self.assertNotIn('tools',payload)
            self.assertEqual(payload['text']['format']['type'],'json_schema')
            self.assertTrue(payload['text']['format']['strict']);self.assertEqual(result['citations'][0]['quote'],'Cria site')

    def test_unavailable_or_false_citation_is_uncertain_without_retry(self):
        for reply in [self.response('Não existe no excerto'),{**self.response(),'status':'incomplete'}]:
            with patch('urllib.request.build_opener') as transport:
                transport.return_value.open.return_value=io.BytesIO(json.dumps(reply).encode())
                with self.assertRaises(ProviderFailure) as error:converse('Criar site',self.context())
                self.assertTrue(error.exception.uncertain);self.assertEqual(transport.return_value.open.call_count,1)
