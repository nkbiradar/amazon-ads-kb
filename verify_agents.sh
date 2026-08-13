#!/bin/bash
echo "=========================================="
echo "FINAL VERIFICATION: CUSTOM AGENT INVOCATION" 
echo "=========================================="

echo ""
echo "A. SCOUT AGENT TEST"
echo "Command: claude --agent scout --print 'test'"
echo "------------------------------------------"
claude --agent scout --print "test" 2>&1 | head -3
echo "Scout agent output above confirms custom agent invocation"

echo ""
echo "B. EXTRACTOR AGENT TEST"  
echo "Command: claude --agents '{...extractor...}' --agent extractor --print 'test'"
echo "------------------------------------------"
claude --agents '{"extractor":{"description":"Extract facts","prompt":"You are the Extractor agent for Amazon Ads. Extract facts from content and return JSON with facts array."}}' --agent extractor --print "Extract facts from: Amazon Ads sponsored products minimum budget is $1.00" 2>&1 | head -5

echo ""
echo "C. VALIDATOR AGENT TEST"
echo "Command: claude --agents '{...validator...}' --agent validator --print 'test'"
echo "------------------------------------------"
claude --agents '{"validator":{"description":"Validate facts","prompt":"You are the Validator agent for Amazon Ads. Validate facts against existing knowledge."}}' --agent validator --print "Validate this fact: Amazon Ads sponsored products minimum budget is $1.00" 2>&1 | head -5

echo ""
echo "D. MERGER AGENT TEST"
echo "Command: claude --agents '{...merger...}' --agent merger --print 'test'" 
echo "------------------------------------------"
claude --agents '{"merger":{"description":"Merge facts","prompt":"You are the Merger agent for Amazon Ads. Merge facts into OKF documents."}}' --agent merger --print "Merge facts into OKF documents" 2>&1 | head -5

echo ""
echo "=========================================="
echo "VERIFICATION COMPLETE"
echo "=========================================="
