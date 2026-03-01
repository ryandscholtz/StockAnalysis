$profile = "cerebrum"
$region = "eu-west-1"
$roleName = "StockAnalysisInfrastructu-LambdaExecutionRoleD5C260-kW9wvngtVo2R"

Write-Host "=== Attached Policies ==="
aws iam list-attached-role-policies `
    --role-name $roleName `
    --profile $profile `
    --output json | ConvertFrom-Json | Select-Object -ExpandProperty AttachedPolicies | ForEach-Object {
    Write-Host "  $($_.PolicyName) - $($_.PolicyArn)"
}

Write-Host ""
Write-Host "=== Inline Policies ==="
aws iam list-role-policies `
    --role-name $roleName `
    --profile $profile `
    --output json | ConvertFrom-Json | Select-Object -ExpandProperty PolicyNames | ForEach-Object {
    Write-Host "  $_"
    $doc = aws iam get-role-policy --role-name $roleName --policy-name $_ --profile $profile --output json | ConvertFrom-Json
    $doc.PolicyDocument | ConvertTo-Json -Depth 10
}
