;;; EDU45.il
;;; GPDK045 / IC6.1.8 layout generator (educational scaffold)
;;;
;;; Load in Virtuoso CIW:
;;;   load("/path/to/EDU45.il")
;;;
;;; Python (skillbridge):
;;;   ws.EDU_make_layout("EDU45", "NAND2", "nand", 2, 0.24, 0.24, 0.045, 0.30)
;;;
;;; Notes:
;;;   - GPDK045 library name is "gpdk045" (install dir is gpdk045_v_6_0).
;;;   - Layer names are Metal1, Oxide, Poly, Nimp, Pimp, Nwell, Cont, Via1.
;;;     Do NOT use M1 or OD.
;;;   - pcell parameter names are usually w, l, nf, m.
;;;     Verify with "q" on a manually placed instance; types may differ.
;;;   - This file only PLACES devices and rails. Routing, pins, taps,
;;;     well/implant enclosures and DRC/LVS cleanup are not included.

;; ---------------------------------------------------------------------------
;; Basic helpers
;; ---------------------------------------------------------------------------
procedure(EDU_mos(cv master name x y w l nf m)
  let((params)
    params = list(
      list("w"  "float" w)
      list("l"  "float" l)
      list("nf" "int"   nf)
      list("m"  "int"   m)
    )
    dbCreateParamInstByMasterName(
      cv "gpdk045" master "layout" name list(x y) "R0" 1 params
    )
  )
)

procedure(EDU_rails(cv width ytop)
  ;; VSS rail at y = -0.10 .. 0.0, VDD rail at y = ytop .. ytop + 0.10
  dbCreateRect(cv "Metal1" list(0.0 -0.10 width 0.0))
  dbCreateRect(cv "Metal1" list(0.0 ytop width (ytop + 0.10)))
)

;; ---------------------------------------------------------------------------
;; Inverter
;; ---------------------------------------------------------------------------
procedure(EDU_inv_lay(cv wn wp l pitch)
  EDU_mos(cv "nmos1v" "MN0" 0.0 0.0 wn l 1 1)
  EDU_mos(cv "pmos1v" "MP0" 0.0 pitch wp l 1 1)
  EDU_rails(cv 0.60 (* 2.0 pitch))
)

;; ---------------------------------------------------------------------------
;; NAND-n: n NMOS in series (vertical), n PMOS in parallel (horizontal)
;; ---------------------------------------------------------------------------
procedure(EDU_nand_lay(cv n wn wp l pitch)
  let((i)
    for(i 0 (n - 1)
      EDU_mos(cv "nmos1v" sprintf(nil "MN%d" i) 0.0 (i * pitch) wn l 1 1)
    )
    for(i 0 (n - 1)
      EDU_mos(cv "pmos1v" sprintf(nil "MP%d" i) 0.90 (i * pitch) wp l 1 1)
    )
    EDU_rails(cv 1.80 (n * pitch))
  )
)

;; ---------------------------------------------------------------------------
;; NOR-n: n NMOS in parallel (horizontal), n PMOS in series (vertical)
;; ---------------------------------------------------------------------------
procedure(EDU_nor_lay(cv n wn wp l pitch)
  let((i)
    for(i 0 (n - 1)
      EDU_mos(cv "nmos1v" sprintf(nil "MN%d" i) 0.0 (i * pitch) wn l 1 1)
    )
    for(i 0 (n - 1)
      EDU_mos(cv "pmos1v" sprintf(nil "MP%d" i) 0.90 (i * pitch) wp l 1 1)
    )
    EDU_rails(cv 1.80 (n * pitch))
  )
)

;; ---------------------------------------------------------------------------
;; MUX layout stubs
;; ---------------------------------------------------------------------------
procedure(EDU_mux2_lay(cv wn wp l pitch)
  printf("EDU: MUX2 layout template is not implemented yet.\n")
  printf("EDU: place 4 TG devices + select inverter, then route.\n")
)

;; ---------------------------------------------------------------------------
;; Entry point called from Python / skillbridge
;; ---------------------------------------------------------------------------
procedure(EDU_make_layout(lib cell kind n wn wp l pitch)
  let((cv)
    cv = dbOpenCellViewByType(lib cell "layout" "maskLayout" "a")
    cond(
      ((equal(kind "inv")  (EDU_inv_lay  cv wn wp l pitch)))
      ((equal(kind "nand") (EDU_nand_lay cv n wn wp l pitch)))
      ((equal(kind "nor")  (EDU_nor_lay  cv n wn wp l pitch)))
      ((equal(kind "mux2") (EDU_mux2_lay cv wn wp l pitch)))
      ((equal(kind "mux4") (EDU_mux2_lay cv wn wp l pitch)))
      (t (printf("EDU: unsupported kind %s\n" kind)))
    )
    dbSave(cv)
    cv
  )
)

;; ---------------------------------------------------------------------------
;; Optional: list GPDK045 layers (uncomment if techGetTechFile works in your IC618)
;; ---------------------------------------------------------------------------
;; procedure(EDU_list_layers()
;;   let((tf)
;;     tf = techGetTechFile(ddGetObj("gpdk045"))
;;     foreach(layer tf->layerDefinitions
;;       printf("%s\n" layer->name)
;;     )
;;   )
;; )
