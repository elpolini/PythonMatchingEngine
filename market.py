# -*- coding: utf-8 -*-
"""
Created on Thu May 16 14:14:51 2019

@author: Francisco Merlos
"""
from abc import ABC, abstractmethod
import time 

class Market():

    def __init__(self):
        self.bids = Bids()
        self.asks = Asks()
        self.trades = []
        # keeps track of all orders sent to the market
        # allows fast access of orders status by uid
        self.orders = dict()        
        self.last_uid = 0 
		
    def send(self, is_buy, qty, price, timestamp = time.time()):
        """ Send new order to market
            Passive orders can't be matched and will be added to the book
            Aggressive orders are matched against opp. side's resting orders
            
            Params:
                is_buy (bool): True if it is a buy order
                qty (int): initial quantity or size of the order 
                price (float): limit price of the order
                timestamp (float): time of processing 
                
            Returns:
                self.last_uid (int): order unique id set by the market 
        """
        
        self.last_uid += 1 
        neword = Order(self.last_uid, is_buy, qty, price, timestamp)
        self.orders.update({self.last_uid:neword})
        while (neword.leavesqty > 0):
            if self.is_aggressive(neword):            
                self.sweep_best_price(neword)    
            else:
                if is_buy:
                    self.bids.add(neword)            
                else:
                    self.asks.add(neword)            
                return self.last_uid
                
    
    def cancel(self, uid): 
        order = self.orders[uid]
        if order.is_buy:
            pricelevel = self.bids.book[order.price]
        else:
            pricelevel = self.asks.book[order.price]
    
        # right side
        if order.next is None:
            pricelevel.tail = order.prev
            if order is pricelevel.head:
                self.remove_price(order.is_buy, order.price)                
            else:
                order.prev.next = None        
        # left side
        elif order is pricelevel.head:
            pricelevel.head = order.next
            order.next.prev = None
        # middle
        else:
            order.next.prev = order.prev
            order.prev.next = order.next            

        order.leavesqty = 0 
        return
    
    

    def is_aggressive(self, Order):
        is_agg = True
        if Order.is_buy:
            if self.asks.best is None or self.asks.best.price > Order.price:
                is_agg = False
        else:
            if self.bids.best is None or self.bids.best.price < Order.price:
                is_agg = False
        return is_agg 
    
    def sweep_best_price(self, Order):        
        if Order.is_buy:            
            best = self.asks.best
        else:
            best = self.bids.best        
        while(Order.leavesqty > 0):
            if best.head.leavesqty <= Order.leavesqty:                
                trdqty = best.head.leavesqty
                best.head.leavesqty = 0
                self.trades.append([best.price, trdqty])
                best.pop()                
                Order.leavesqty -= trdqty
                if best.head is None:
                    # remove PriceLevel from the order's opposite side
                    self.remove_price(not Order.is_buy, best.price)
                    break
            else:
                self.trades.append([best.price, Order.leavesqty])
                best.head.leavesqty -= Order.leavesqty
                Order.leavesqty = 0
        
    def remove_price(self, is_buy, price):
        if is_buy:
            del self.bids.book[price]
            if len(self.bids.book)>0:
                self.bids.best = self.bids.book[max(self.bids.book.keys())]
            else:
                self.bids.best = None
        else:
            del self.asks.book[price]
            if len(self.asks.book)>0:
                self.asks.best = self.asks.book[min(self.asks.book.keys())]
            else:
                self.asks.best = None
            
                   
                
class Order():
    """ Represents an order inside the market with its current status 
    
    """
    #__slots__ = ["uid", "is_buy", "qty", "price", "timestamp", "status"]        
    
    def __init__(self, uid, is_buy, qty, price, timestamp = time.time()):
        self.uid = uid
        self.is_buy = is_buy
        self.qty = qty
        self.cumqty = 0
        # outstanding volume in market. If filled or canceled => 0. 
        self.leavesqty = qty
        self.price = price
        self.timestamp = timestamp  
        # is the order active and resting in the orderbook?
        self.active = False         
        # DDL attributes import unittest
        self.prev = None
        self.next = None
        
    
        
        
    
class PriceLevel():
    """ Represents a price in the orderbook with its order queue
    
    """
    def __init__(self, Order):
        self.price = Order.price 
        self.head = Order
        self.tail = Order
            
    def append(self, Order):        
        self.tail.next = Order
        Order.prev = self.tail
        self.tail = Order
    
    def pop(self):
        self.head.active = False
        if self.head.next is None:         
            self.head = None
            self.tail = None
        else:
            self.head.next.prev = None            
            self.head = self.head.next
            
        
class OrderBook():
    """ Bids or Asks orderbook with different PriceLevels
    
    """
    def __init__(self):        
        self.book = dict()
        # Pointer to Best PriceLevel 
        self.best = None
	
    def add(self, Order):
        if Order.price in self.book:
            self.book[Order.price].append(Order)
        else:
            new_pricelevel = PriceLevel(Order)
            self.book.update({Order.price:new_pricelevel})
            if self.best is None or self.is_new_best(Order):
                self.best = new_pricelevel
        Order.active = True
    
    @abstractmethod
    def is_new_best(self, Order):
        pass
        

class Bids(OrderBook):
    """ Bids Orderbook where best PriceLevel has highest price
        Implements is_new_best abstract method that behaves differently
        for Bids or Asks
    """
    def __init__(self):
        super().__init__()
    
    def is_new_best(self, Order):        
        if Order.price > self.best.price:
            return True
        else:
            return False
    
class Asks(OrderBook):
    """ Asks Orderbook where best PriceLevel has lowest price
        Implements is_new_best abstract method that behaves differently
        for Bids or Asks
    """
    def __init__(self):
        super().__init__()
        
    def is_new_best(self, Order):
        if Order.price < self.best.price:
            return True
        else:
            return False
        