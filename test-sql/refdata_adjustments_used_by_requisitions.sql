SELECT * FROM referencedata.stock_adjustment_reasons WHERE id IN 
(SELECT reasonid FROM requisition.stock_adjustments);	