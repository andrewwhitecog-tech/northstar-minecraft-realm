import hashlib
from pathlib import Path
import tempfile
import unittest
import baseline_paint as B
import representative_painter as P
import render_four_views as R

class RepresentativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.cfg,cls.models=P.model_sources()

    def test_only_four_selected_looks_no_expanded_catalog(self):
        self.assertEqual(set(self.models),{'domestic_bengal','domestic_maine_coon','domestic_sphynx','fantasy_obsidian_rainbow'})
        self.assertEqual(len(self.cfg['entries']),4)

    def test_rosette_center_is_open_copper_inner_and_dark_ring(self):
        ct,ch,rt,rh,rot,opening=P.ROSETTES[0]
        ct+=.018*P.math.sin(ch*9)
        self.assertEqual(P.rosette_mask(ct,ch),'center')
        tags={P.rosette_mask(ct+rt*u/10,ch+rh*v/10) for u in range(-12,13) for v in range(-12,13)}
        self.assertTrue({'rim','copper','center','coat'}<=tags)
        # The whole center column cannot be a solid stripe.
        self.assertNotEqual(P.rosette_mask(ct,ch),P.rosette_mask(ct,ch+rh*.9))

    def test_resolution_is_scaled_uv_not_resized_previous_image(self):
        m=self.models['domestic_bengal']['adult']
        a=P.paint('domestic_bengal',m,1); b=P.paint('domestic_bengal',m,4)
        self.assertEqual(a[:2],(64,32)); self.assertEqual(b[:2],(256,128))
        self.assertEqual(len(b[2]),256*128*4)
        # HD painter samples independently: at least one4x4texel block contains detail.
        varying=False
        for y in range(32):
            for x in range(64):
                colors={b[2][((y*4+dy)*256+x*4+dx)*4:((y*4+dy)*256+x*4+dx)*4+4] for dy in range(4) for dx in range(4)}
                if len(colors)>1: varying=True;break
            if varying: break
        self.assertTrue(varying)

    def test_geometry_has_real_ruff_tuft_muzzle_and_no_tool_fields_in_export(self):
        maine=self.models['domestic_maine_coon']['bedrock']
        self.assertIn('ear_tuft',{c['region'] for c in maine['cubes']}); self.assertIn('ruff',{c['region'] for c in maine['cubes']})
        for name,models in self.models.items():
            for m in models.values():
                for c in m['cubes']: B.validate_cube(c,m['width'],m['height'])
            for bone in models['bedrock']['geometry']['minecraft:geometry'][0]['bones']:
                self.assertFalse(any('paintRegion' in c for c in bone.get('cubes',[])))

    def test_obsidian_anatomy_stays_dark_with_nonempty_prismatic_ink(self):
        colors=[P.coat_color('fantasy_obsidian_rainbow','body','west',.2,h/40,t/60) for h in range(41) for t in range(61)]
        dark=sum(max(c)<90 for c in colors); vivid=sum(max(c)-min(c)>90 for c in colors)
        self.assertGreater(dark/len(colors),.6); self.assertGreater(vivid,0)

    def test_png_file_roundtrip_and_bad_crc_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'pixels.png'; pixels=bytes([11,22,33,255]*4)
            path.write_bytes(B.png_bytes(2,2,pixels)); self.assertEqual(R.decode_png(path),(2,2,pixels))
            broken=bytearray(path.read_bytes()); broken[20]^=1;path.write_bytes(broken)
            with self.assertRaises(ValueError): R.decode_png(path)

    def test_actual_textured_geometry_two_views_have_depth_and_different_pixels(self):
        with tempfile.TemporaryDirectory() as d:
            m=self.models['domestic_bengal']['baby']; w,h,pixels,_=P.paint('domestic_bengal',m,4)
            texture=Path(d)/'baby.png';texture.write_bytes(B.png_bytes(w,h,pixels))
            a,ar=R.render(m,texture,64,0,.16); b,br=R.render(m,texture,64,1.1,.16)
            self.assertGreater(ar['modelPixels'],0); self.assertGreater(ar['depthMax'],ar['depthMin'])
            self.assertGreater(br['modelPixels'],0); self.assertNotEqual(hashlib.sha256(a).digest(),hashlib.sha256(b).digest())
            self.assertEqual(ar['modelTriangles'],len(m['cubes'])*12)

    def test_renderer_rejects_bad_size_scale_and_aspect(self):
        m=self.models['domestic_sphynx']['baby']
        with self.assertRaises(ValueError): P.paint('domestic_sphynx',m,2)
        with self.assertRaises(ValueError): R.render(m,'not-read.png',32)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.png';p.write_bytes(B.png_bytes(2,1,bytes([0,0,0,255]*2)))
            with self.assertRaisesRegex(ValueError,'aspect'): R.render(m,p,64)

if __name__=='__main__': unittest.main(verbosity=2)
