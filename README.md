# adjustment-reason-migration
Cross service migration of adjustment reasons used by requisition - from referencedata to stock management.

This performs the migration of reasons from the Referencedata service to the Stock Management service, as well
as the migration of Requisition adjutments to use the UUIDs of the reasons in stock management.

These script will execute these steps:
1) Retrieve all facility types from Referencedata
2) Retrieve all adjustment reasons from Referencedata
3) Retrieve all valid reasons assignments joined with stock reasons from Stock Management
4) For reach reason from Referencedata and each facility type, do:
    * Check if a valid reason assignment exists for the facility type/program combo. The stock reason associated must
    have a matching name, description and type(CREDIT/DEBIT). Comparisons for name and description are case insensitive.
    If such a reason exists in Stock Management, we store a mapping between it and the refdata reason in the memory.
    * If no assignment exists for program and facility type, check if a matching stock reason exists at all (matching 
    described in the previous step) If yes, a valid reason assignment is inserted into the db and associated with the
    matched reason. A mapping to the valid reason assignment from the Referencedata reason is stored in memory.
    * If no matching reason exists at all, both a stock reason and a valid reason assignment are created. The mapping is
    also stored.

After the steps above are complete, the reasons from Referencedata are now migrated to stock management. The output of
this phase is a map, in which each combo of facility type and a Referencedata reason id is mapped to a valid reason
assignment ID in Stock Management. 

In the next phase, we migrate existing adjustments in Requisition to point to Stock reasons instead of Referencedata reasons.

These steps are executed:
1) Fetch all valid assignment ids from stock for reference
2) Fetch all facilities and map them to facility types
3) Fetch a join between the stock adjustments, requisition line items and requisitions. Do this in batch of 2000, while iterating
over each row.
4) For each of the rows, check if the ID of the reasons comes from Stock. If yes, do nothing for this row.
5) If not, we figure out the facility type based on the facility from the requisition. Based on the facility type and the
ID of the reason from Referencedata, we get the ID of the reason in Stock from our map created in phase 1.
   