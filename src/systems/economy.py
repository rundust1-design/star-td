"""
经济系统 — 管理金钱、收入和支出
"""


class Economy:
    """塔防经济系统"""

    def __init__(self, starting_money: int = 200):
        self.money = starting_money
        self.total_earned = 0
        self.total_spent = 0

    def can_afford(self, cost: int) -> bool:
        """检查是否可以支付"""
        return self.money >= cost

    def spend(self, cost: int) -> bool:
        """消费，成功后返回 True"""
        if self.can_afford(cost):
            self.money -= cost
            self.total_spent += cost
            return True
        return False

    def earn(self, amount: int):
        """获得金钱"""
        self.money += amount
        self.total_earned += amount

    def get_refund(self, total_cost: int, ratio: float = 0.5) -> int:
        """计算出售退款"""
        return int(total_cost * ratio)
