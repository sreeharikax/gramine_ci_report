## Parameters

**rerun_details**: 
These are the format should be used when we need to update the job run
details. It should be specified only if we want to update/replace the existing
result for the job

    * If any job is triggered for 2nd time
        ```
        {"local_ci_graphene_native_dcap":{"244":"245"}, "local_ci_graphene_sgx_dcap":{"295":"302"}}
        ```

    * If for some reason, build did not get scheduled
        ```
        {"local_ci_graphene_gsc_debian_11": {"add":"7"}}
        ```

    * We have many pipelines who has same job but triggered with different parameters, if you have more than 1 job failure then specify in below format
        ```
        {"local_ci_graphene_sgx_build_without_prefix": [{"1021": "1025"}, {"1023": "1026"}]}
        ```

**nightly_pipeline**: Name of the pipeline

**build_no**: By default it will take latest build number, specify another build
no to override
