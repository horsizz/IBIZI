SELECT P.Name, sum(Store.Quantity) amount, 
CASE
	when sum(Store.Quantity) < 0 then '������'
	when sum(Store.Quantity) < 400 then '����'
	when sum(Store.Quantity) >= 400 and sum(Store.Quantity) < 1000 then '����������'
	when sum(Store.Quantity) > 1000 then '���������'
END as ������
FROM Store inner join Product p on p.id = Store.id_Product
GROUP by P.Name --1

SELECT 
    P.Name AS '������������', 
    SUM(S.Quantity) AS '����������'
FROM Store S
JOIN Product P ON S.id_Product = P.id
WHERE S.Quantity BETWEEN 1 AND 500
GROUP BY P.Name;


SELECT TOP 3
    P.Name AS '������������', 
    SUM(D.Amount * S.Price) AS '�����'
FROM Deal D
JOIN Store S ON D.StoreID = S.id
JOIN Product P ON S.id_Product = P.id
GROUP BY P.Name
ORDER BY '�����' DESC;--3

SELECT 
    P.Name AS '������������',
    YEAR(D.Date) AS '���',
    FORMAT(D.Date, 'MMMM', 'ru-RU') AS '�����',
    SUM(D.Amount * S.Price) AS TotalSales
FROM Deal D
JOIN Store S ON D.StoreID = S.id
JOIN Product P ON S.id_Product = P.id
GROUP BY P.Name, YEAR(D.Date), FORMAT(D.Date, 'MMMM', 'ru-RU')
ORDER BY '���', '�����', '������������';

--4

SELECT 
	P.Name as '������������',
    YEAR(D.Date) AS '���',
    FORMAT(D.Date, 'MMMM', 'ru-RU') AS '�����',
    SUM(D.Amount * S.Price) AS '�����'
FROM Deal D
JOIN Store S ON D.StoreID = S.id
JOIN Product P ON S.id_Product = P.id
WHERE P.Name = 'Wine - Fume Blanc Fetzer'
GROUP BY P.Name,YEAR(D.Date), FORMAT(D.Date, 'MMMM', 'ru-RU')
HAVING SUM(D.Amount * S.Price) < 300
ORDER BY '���', '�����';
 --5
