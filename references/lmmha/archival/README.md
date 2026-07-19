# LMMHA Archival Copies

Local archival copies of older LMMHA records found outside the current CGA
publication surface.

## 1987 eLibrary / Parliament Library record

- Title: `List of Major and Minor Heads of Account of Union and States 1987`
- Public handle: <https://elibrary.sansad.in/handle/123456789/53283>
- eLibrary item UUID: `65ffdef0-8e5a-4f58-b811-39f0d74f8e6e`
- Author metadata: `India. Ministry of Finance. Department of Expenditure`
- Issued: `1987`
- Accession number: `RC74391(1)`
- Call number: `351.71R M7`
- Original bitstream: `RP-RC74391-1.pdf`
- Original bitstream UUID: `7e058dde-7c78-442c-b132-5c853de638a1`
- Original bitstream size: `88,944,846` bytes
- Original bitstream MD5: `21b6ed7bf7712b6f4b78bb3f2cbcb4a0`
- OCR text bitstream: `RP-RC74391-1.pdf.txt`
- OCR text bitstream UUID: `92fa5f26-29b0-4c93-901b-54608809269f`

Local filenames:

- `commoner_probe_lmmha_1987/pdfs/RP-RC74391-1.pdf`
- `commoner_probe_lmmha_1987/manifest.jsonl`
- `commoner_probe_lmmha_1987/probe.log`
- `LMMHA_1987_eLibrary_RP-RC74391-1.pdf.txt`
- `LMMHA_1987_eLibrary_item.json`
- `LMMHA_1987_eLibrary_original_bitstreams.json`

The PDF was pulled through `commoner-probe` using
`SansadProbe.ls_pdf_url()` and `SansadProbe.write_pdf()`. The run manifest
records `88,944,846` actual bytes and MD5
`21b6ed7bf7712b6f4b78bb3f2cbcb4a0`, matching the eLibrary bitstream
metadata. Local `pdfinfo` reports a 480-page PDF, version 1.7, file size
`88,944,846` bytes. A text sample from pages 2-5 identifies the volume as the
`List of Major and Minor Heads Account of Union and States` issued by the
Ministry of Finance, Department of Expenditure, Controller General of Accounts.

Verification caveat: the eLibrary item metadata says `dc.format.printedpages`
is `4p`, while the original PDF bitstream and local `pdfinfo` report a 480-page
document. Treat the handle as the archival source record and cite the
probe-verified PDF copy, not the item-level printed-page metadata, for page
count or content claims.
