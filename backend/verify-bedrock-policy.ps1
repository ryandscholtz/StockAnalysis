$roleName = "StockAnalysisInfrastructu-LambdaExecutionRoleD5C260-kW9wvngtVo2R"
$result = aws iam get-role-policy --role-name $roleName --policy-name "BedrockAccess" --profile cerebrum --output json | ConvertFrom-Json
$result.PolicyDocument | ConvertTo-Json -Depth 10
