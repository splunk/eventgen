HTTP_INPUTS_PATH=/opt/splunk/etc/apps/search/local/inputs.conf
echo "[test]" >> $HTTP_INPUTS_PATH
echo "disabled = 0" >> $HTTP_INPUTS_PATH
echo "token = 00000000-0000-0000-0000-000000000000" >> $HTTP_INPUTS_PATH
echo "indexes = main,test_0,test_1" >> $HTTP_INPUTS_PATH
