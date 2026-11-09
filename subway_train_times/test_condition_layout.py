"""Keep complete weather conditions readable instead of an ambiguous 'Mostly...'."""
import copy
import io
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
import home_edit
import subway_server as server
from test_home_edit import WEATHER, NOW, FixedDateTime


class ConditionLayoutTests(unittest.TestCase):
    def test_complete_labels_fit_their_region_in_both_layouts(self):
        cases = {0:'Clear',1:'Mostly clear',2:'Partly cloudy',3:'Cloudy',45:'Foggy',
                 51:'Rain',61:'Rain',71:'Snow',85:'Snow',95:'Storms',None:'Unavailable'}
        for code, expected in cases.items():
            for reminders in ([],[{'title':'Water the plants'}]):
                weather=copy.deepcopy(WEATHER);weather['current']['weather_code']=code
                with patch.object(home_edit,'_text',wraps=home_edit._text) as draw:
                    home_edit.render(NOW,weather,37,reminders=reminders)
                call=next(c for c in draw.call_args_list if c.args[1]==186)
                self.assertEqual(call.args[3],expected)
                f=home_edit.font(call.args[4],'mono')
                self.assertLessEqual(f.getlength(expected),190)
                self.assertEqual(home_edit._fit_text(ImageDraw.Draw(Image.new('L',(800,480))),expected,f,190),expected)

    def test_real_route_produces_complete_mostly_clear_preview(self):
        weather=copy.deepcopy(WEATHER);weather['current']['weather_code']=1
        with patch.object(server,'datetime',FixedDateTime),patch.object(server,'load_config',return_value={}),patch.object(server,'get_weather',return_value=weather),patch.object(server,'get_air_quality',return_value=37),patch.object(server.overlay_store,'active',return_value=[]):
            response=server.app.test_client().get('/display.bmp')
        self.assertEqual(response.status_code,200)
        image=Image.open(io.BytesIO(response.data))
        self.assertEqual((image.size,image.mode),((800,480),'1'))
        image.save('/opt/data/artifacts/eink/field-notes-deploy/label-fit-preview.png')


if __name__=='__main__':unittest.main()
