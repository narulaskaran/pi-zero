"""Offline acceptance tests for the shared-home board. No live writes/network."""
import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import subway_server as server
import home_edit

REAL_GET_AIR_QUALITY = server.get_air_quality

WEATHER = {
    'current': {'temperature_2m':53, 'apparent_temperature':47, 'weather_code':0},
    'daily': {'time':['2026-11-08','2026-11-09'], 'temperature_2m_max':[61,56],
              'temperature_2m_min':[46,43], 'precipitation_probability_max':[17,4],
              'sunrise':['2026-11-08T06:34','2026-11-09T06:35'],
              'sunset':['2026-11-08T16:44','2026-11-09T16:43']}}
NOW = datetime(2026,11,8,18,0)

class HomeEditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)
        self.patches=[patch.object(server,'load_config',return_value={}),
                      patch.object(server.overlay_store,'OVERLAY_FILE',self.state/'overlays.json'),
                      patch.object(server.overlay_store,'IMAGE_DIR',self.state/'images'),
                      patch.object(server,'get_air_quality',return_value=25)]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def test_refresh_is_fifteen_minutes_even_with_old_config(self):
        with patch.object(server,'load_config',return_value={'refresh_rate':{'intervals':{'fast':60,'slow':1800,'night':1800}}}):
            self.assertEqual(server.calculate_refresh_rate(),900)
            c=server.app.test_client()
            self.assertEqual(c.get('/refresh-rate').json['refresh_minutes'],15)
            self.assertEqual(c.get('/status').json['layout'],'home_edit')

    def test_no_transit_requests_and_real_weather_fields(self):
        with patch.object(server,'get_subway',side_effect=AssertionError('Transit must not be requested'),create=True):
            image=server.generate_image(now=NOW,weather=WEATHER)
        self.assertEqual(image.size,(800,480))
        image.save(self.state/'normal.png')

    def test_missing_sparse_and_extreme_weather(self):
        for w in [{}, {'current':{}}, {'current':{'temperature_2m':-12,'apparent_temperature':-30,'weather_code':95}}, {'daily':{'time':[]}}]:
            self.assertEqual(server.generate_image(now=NOW,weather=w).size,(800,480))

    def test_footer_selects_tomorrow_by_date_not_position(self):
        self.assertEqual(home_edit.forecast_index(WEATHER,NOW),1)
        self.assertIsNone(home_edit.forecast_index(WEATHER,datetime(2026,11,12)))

    def test_long_overlay_is_ellipsized_and_slots_do_not_crash(self):
        for slot in ['banner','sidebar','fullscreen']:
            o={'id':'test','slot':slot,'title':'A very long reminder title '*5,'text':'Very long household reminder '*40}
            im=home_edit.render(NOW,WEATHER,25)
            home_edit.draw_overlay(im,o)
            self.assertEqual(im.size,(800,480))

    def test_overlay_crud_and_bmp_contract(self):
        c=server.app.test_client()
        r=c.post('/overlay',json={'id':'test-home','slot':'banner','title':'Household','text':'Test only','ttl_seconds':60})
        self.assertEqual(r.status_code,201)
        self.assertEqual(c.get('/overlays?active=1').json['overlays'][0]['id'],'test-home')
        with patch.object(server,'get_weather',return_value=WEATHER):
            response=c.get('/display.bmp?battery=73')
        self.assertEqual(response.status_code,200)
        im=Image.open(io.BytesIO(response.data))
        self.assertEqual(im.mode,'1'); self.assertEqual(im.size,(800,480))
        self.assertLess(len(response.data),50000)
        self.assertEqual(c.delete('/overlay/test-home').status_code,200)
        self.assertEqual(c.get('/overlays?active=1').json['overlays'],[])

    def test_network_failure_is_explicit(self):
        with patch.object(server.requests,'get',side_effect=OSError('offline')):
            self.assertIsNone(server.get_weather(40,-74))
            server._air_cache.clear()
            self.assertIsNone(REAL_GET_AIR_QUALITY(40,-74))
        im=home_edit.render(NOW,None,None)
        self.assertEqual(im.size,(800,480))

if __name__=='__main__': unittest.main()
