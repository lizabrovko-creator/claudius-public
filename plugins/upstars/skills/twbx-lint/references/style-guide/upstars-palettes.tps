<?xml version='1.0'?>
<!--
  Upstars Tableau Style Guide — Color Palettes
  Source: "Tableau Style Guide v2" (23 pp.) by Anna Kaznacheieva.

  INSTALL:
    Windows : Documents\My Tableau Repository\Preferences.tps
    macOS   : ~/Documents/My Tableau Repository/Preferences.tps
  If a Preferences.tps already exists, merge the <color-palette> blocks below
  into its existing <preferences> element (keep a single <workbook>/<preferences>).
  Then restart Tableau Desktop.

  v2 CHANGES vs v1: Main pos.5/6 -> #C2660A/#0E9FBF; Light pos.4/8 ->
  #6EEDD4/#F5CE9E; Alternative 6->7 colours (#7D84B2 -> #6EC3D8, +#DF90D8);
  Sequential 6->8 palettes (light end unified to #F3F3F3, new S3 Red +
  S8 Grey-White, Orange renamed Amber); Divergent 9->7 (D1/D2 right shoulder
  Blue->Purple, greens -> #3FB587, new D6 Red-Amber-Green, dropped the two
  Light-Red variants and Upstars Blue); RAG#1 -> #E0A030/#3FB587,
  RAG#2 green -> #9CE8CC.
  NOTE: the guide prints S3 Red's end label as #005DE8 (a copy-paste of
  S6 Blue). The swatch itself renders #D04747, which is the value used here.
-->
<workbook>
  <preferences>

    <!-- ============== CATEGORICAL ============== -->
    <color-palette name="UPSTARS Main" type="regular">
      <color>#5535BE</color>
      <color>#210E5F</color>
      <color>#12CC2A</color>
      <color>#FFE200</color>
      <color>#C2660A</color>
      <color>#0E9FBF</color>
      <color>#EF50CC</color>
      <color>#005DE8</color>
      <color>#D04747</color>
    </color-palette>

    <color-palette name="UPSTARS Light" type="regular">
      <color>#928EEC</color>
      <color>#A6FFB1</color>
      <color>#FFF393</color>
      <color>#6EEDD4</color>
      <color>#FFB1EE</color>
      <color>#9CC4FF</color>
      <color>#FFA2A2</color>
      <color>#F5CE9E</color>
      <color>#CECED6</color>
    </color-palette>

    <color-palette name="UPSTARS Alternative" type="regular">
      <color>#8794D5</color>
      <color>#EDC948</color>
      <color>#59CD90</color>
      <color>#FF9D85</color>
      <color>#6EC3D8</color>
      <color>#DF90D8</color>
      <color>#CECED6</color>
    </color-palette>

    <color-palette name="UPSTARS Purple-Grey" type="regular">
      <color>#210E5F</color>
      <color>#5535BE</color>
      <color>#928EEC</color>
      <color>#D9D8FF</color>
      <color>#CECED6</color>
      <color>#A5A5AC</color>
      <color>#81818E</color>
    </color-palette>

    <color-palette name="UPSTARS Blue-Grey" type="regular">
      <color>#003E9B</color>
      <color>#005DE8</color>
      <color>#3888FF</color>
      <color>#9CC4FF</color>
      <color>#CECED6</color>
      <color>#A5A5AC</color>
      <color>#81818E</color>
    </color-palette>

    <!-- ============== RAG STATUS ============== -->
    <color-palette name="RAG 1" type="regular">
      <color>#D04747</color>
      <color>#E0A030</color>
      <color>#3FB587</color>
    </color-palette>

    <color-palette name="RAG 2" type="regular">
      <color>#FFA2A2</color>
      <color>#FFDE8B</color>
      <color>#9CE8CC</color>
    </color-palette>

    <color-palette name="RAG Alternative" type="regular">
      <color>#FF9D85</color>
      <color>#EDC948</color>
      <color>#59CD90</color>
    </color-palette>

    <!-- ============== SEQUENTIAL ============== -->
    <color-palette name="S1 Purple-Grey" type="ordered-sequential">
      <color>#F3F3F3</color>
      <color>#928EEC</color>
    </color-palette>

    <color-palette name="S2 Purple-White" type="ordered-sequential">
      <color>#FFFFFF</color>
      <color>#928EEC</color>
    </color-palette>

    <color-palette name="S3 Red" type="ordered-sequential">
      <color>#F3F3F3</color>
      <color>#D04747</color>
    </color-palette>

    <color-palette name="S4 Amber" type="ordered-sequential">
      <color>#F3F3F3</color>
      <color>#FFB804</color>
    </color-palette>

    <color-palette name="S5 Green" type="ordered-sequential">
      <color>#F3F3F3</color>
      <color>#3FB587</color>
    </color-palette>

    <color-palette name="S6 Blue" type="ordered-sequential">
      <color>#F3F3F3</color>
      <color>#005DE8</color>
    </color-palette>

    <color-palette name="S7 Blue-Green" type="ordered-sequential">
      <color>#D0FFD6</color>
      <color>#005DE8</color>
    </color-palette>

    <color-palette name="S8 Grey-White" type="ordered-sequential">
      <color>#FFFFFF</color>
      <color>#81818E</color>
    </color-palette>

    <!-- ============== DIVERGENT ============== -->
    <color-palette name="D1 Yellow-White-Purple" type="ordered-diverging">
      <color>#FFB804</color>
      <color>#FFFFFF</color>
      <color>#928EEC</color>
    </color-palette>

    <color-palette name="D2 Yellow-Grey-Purple" type="ordered-diverging">
      <color>#FFB804</color>
      <color>#F3F3F3</color>
      <color>#928EEC</color>
    </color-palette>

    <color-palette name="D3 Red-White-Green" type="ordered-diverging">
      <color>#D04747</color>
      <color>#FFFFFF</color>
      <color>#3FB587</color>
    </color-palette>

    <color-palette name="D4 Red-Grey-Green" type="ordered-diverging">
      <color>#D04747</color>
      <color>#F3F3F3</color>
      <color>#3FB587</color>
    </color-palette>

    <color-palette name="D5 Red-White-Blue" type="ordered-diverging">
      <color>#D04747</color>
      <color>#FFFFFF</color>
      <color>#003E9B</color>
    </color-palette>

    <color-palette name="D6 Red-Amber-Green" type="ordered-diverging">
      <color>#D04747</color>
      <color>#E0A030</color>
      <color>#3FB587</color>
    </color-palette>

    <color-palette name="D7 Upstars Purple" type="ordered-diverging">
      <color>#76E0E7</color>
      <color>#8576E4</color>
      <color>#CA76E7</color>
    </color-palette>

  </preferences>
</workbook>
