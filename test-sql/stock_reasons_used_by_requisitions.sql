SELECT * FROM stockmanagement.stock_card_line_item_reasons WHERE id IN 
(SELECT reasonid FROM requisition.stock_adjustments);	