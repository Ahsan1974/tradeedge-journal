#property script_show_inputs
//+------------------------------------------------------------------+
//| TradeEdge_ExportDeals.mq5                                        |
//| Attach/run this script on any chart in Exness MT5.               |
//| Writes closed XAUUSDm/BTCUSDm deals to:                          |
//|   D:\Trading Dashboard\data\mt5_live\deals.csv                   |
//+------------------------------------------------------------------+
input string ExportPath = "D:\\Trading Dashboard\\data\\mt5_live\\deals.csv";
input int    HistoryDays = 30;
input string SymbolXau   = "XAUUSDm";
input string SymbolBtc   = "BTCUSDm";

int OnStart()
  {
   datetime to_time = TimeCurrent();
   datetime from_time = to_time - HistoryDays * 24 * 60 * 60;
   if(!HistorySelect(from_time, to_time))
     {
      Print("HistorySelect failed: ", GetLastError());
      return(-1);
     }

   int total = HistoryDealsTotal();
   int file = FileOpen(ExportPath, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_REWRITE, ',');
   if(file == INVALID_HANDLE)
     {
      // Fallback into common Files folder if absolute path blocked
      string local = "tradeedge_deals.csv";
      file = FileOpen(local, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON|FILE_REWRITE, ',');
      if(file == INVALID_HANDLE)
        {
         Print("FileOpen failed: ", GetLastError());
         return(-1);
        }
      Print("Wrote common file tradeedge_deals.csv — copy it to data\\mt5_live\\deals.csv");
     }

   FileWrite(file,
             "position_id","ticket","symbol","entry","type","volume","price",
             "profit","commission","swap","fee","time","comment","sl","tp");

   for(int i=0; i<total; i++)
     {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0) continue;
      string sym = HistoryDealGetString(ticket, DEAL_SYMBOL);
      if(sym != SymbolXau && sym != SymbolBtc) continue;
      long dtype = HistoryDealGetInteger(ticket, DEAL_TYPE);
      if(dtype != DEAL_TYPE_BUY && dtype != DEAL_TYPE_SELL) continue;

      long pos_id = HistoryDealGetInteger(ticket, DEAL_POSITION_ID);
      long entry  = HistoryDealGetInteger(ticket, DEAL_ENTRY);
      double volume = HistoryDealGetDouble(ticket, DEAL_VOLUME);
      double price  = HistoryDealGetDouble(ticket, DEAL_PRICE);
      double profit = HistoryDealGetDouble(ticket, DEAL_PROFIT);
      double commission = HistoryDealGetDouble(ticket, DEAL_COMMISSION);
      double swap = HistoryDealGetDouble(ticket, DEAL_SWAP);
      double fee = HistoryDealGetDouble(ticket, DEAL_FEE);
      datetime t = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
      string comment = HistoryDealGetString(ticket, DEAL_COMMENT);

      // SL/TP from related order history when available
      double sl = 0, tp = 0;
      if(HistorySelectByPosition(pos_id))
        {
         int orders = HistoryOrdersTotal();
         for(int o=0; o<orders; o++)
           {
            ulong ot = HistoryOrderGetTicket(o);
            if(ot == 0) continue;
            double osl = HistoryOrderGetDouble(ot, ORDER_SL);
            double otp = HistoryOrderGetDouble(ot, ORDER_TP);
            if(osl != 0) sl = osl;
            if(otp != 0) tp = otp;
           }
         HistorySelect(from_time, to_time);
        }

      FileWrite(file,
                IntegerToString(pos_id),
                IntegerToString((long)ticket),
                sym,
                IntegerToString(entry),
                IntegerToString(dtype),
                DoubleToString(volume, 4),
                DoubleToString(price, 8),
                DoubleToString(profit, 4),
                DoubleToString(commission, 4),
                DoubleToString(swap, 4),
                DoubleToString(fee, 4),
                TimeToString(t, TIME_DATE|TIME_SECONDS),
                comment,
                DoubleToString(sl, 8),
                DoubleToString(tp, 8));
     }

   FileClose(file);
   Print("TradeEdge export complete: ", total, " deals scanned → ", ExportPath);
   return(0);
  }
