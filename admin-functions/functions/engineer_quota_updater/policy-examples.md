# Policy Examples

These are draft statements for the `engineer-quota-updater` function.
Review them in your tenancy before adding them to the admin IAM policy.

## Function Resource Principal

Use this style after the function exists and you have its function OCID:

```text
allow any-user to inspect compartments in tenancy where all {request.principal.type='fnfunc', request.principal.id='<FUNCTION_OCID>'}
allow any-user to manage quotas in tenancy where all {request.principal.type='fnfunc', request.principal.id='<FUNCTION_OCID>'}
```

If you prefer to enable all functions in the function compartment instead of one
specific function, use a dynamic group instead:

```text
ALL {resource.type = 'fnfunc', resource.compartment.id = '<FUNCTION_COMPARTMENT_OCID>'}
```

Then grant the dynamic group:

```text
allow dynamic-group <FUNCTION_DYNAMIC_GROUP_NAME> to inspect compartments in tenancy
allow dynamic-group <FUNCTION_DYNAMIC_GROUP_NAME> to manage quotas in tenancy
```

## Resource Scheduler Invoking The Function

After creating the Resource Scheduler schedule, copy its schedule OCID and
create a dynamic group for that specific schedule:

```text
ALL {resource.type='resourceschedule', resource.id='<RESOURCE_SCHEDULE_OCID>'}
```

Grant that dynamic group access to invoke/manage Functions:

```text
allow dynamic-group <RESOURCE_SCHEDULER_DYNAMIC_GROUP_NAME> to manage functions-family in tenancy
```

You can scope that statement to the function compartment if your tenancy policy
compiler accepts the narrower target:

```text
allow dynamic-group <RESOURCE_SCHEDULER_DYNAMIC_GROUP_NAME> to manage functions-family in compartment <FUNCTION_COMPARTMENT_NAME>
```

## Notes

- Keep `DRY_RUN=true` in `func.yaml` until these policies are active.
- IAM and dynamic group changes can take several minutes to affect resource
  principal tokens.
