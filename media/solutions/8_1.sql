SELECT P.Name, sum(Store.Quantity) amount, 
CASE
	when sum(Store.Quantity) < 0 then 'Ошибка'
	when sum(Store.Quantity) < 400 then 'Мало'
	when sum(Store.Quantity) >= 400 and sum(Store.Quantity) < 1000 then 'Достаточно'
	when sum(Store.Quantity) > 1000 then 'Избыточно'
END as Оценка
FROM Store inner join Product p on p.id = Store.id_Product
GROUP by P.Name --1

SELECT 
    P.Name AS 'Наименование', 
    SUM(S.Quantity) AS 'Количество'
FROM Store S
JOIN Product P ON S.id_Product = P.id
WHERE S.Quantity BETWEEN 1 AND 500
GROUP BY P.Name;


SELECT TOP 3
    P.Name AS 'Наименование', 
    SUM(D.Amount * S.Price) AS 'Сумма'
FROM Deal D
JOIN Store S ON D.StoreID = S.id
JOIN Product P ON S.id_Product = P.id
GROUP BY P.Name
ORDER BY 'Сумма' DESC;--3

SELECT 
    P.Name AS 'Наименование',
    YEAR(D.Date) AS 'Год',
    FORMAT(D.Date, 'MMMM', 'ru-RU') AS 'Месяц',
    SUM(D.Amount * S.Price) AS TotalSales
FROM Deal D
JOIN Store S ON D.StoreID = S.id
JOIN Product P ON S.id_Product = P.id
GROUP BY P.Name, YEAR(D.Date), FORMAT(D.Date, 'MMMM', 'ru-RU')
ORDER BY 'Год', 'Месяц', 'Наименование';

--4

SELECT 
	P.Name as 'Наименование',
    YEAR(D.Date) AS 'Год',
    FORMAT(D.Date, 'MMMM', 'ru-RU') AS 'Месяц',
    SUM(D.Amount * S.Price) AS 'Сумма'
FROM Deal D
JOIN Store S ON D.StoreID = S.id
JOIN Product P ON S.id_Product = P.id
WHERE P.Name = 'Wine - Fume Blanc Fetzer'
GROUP BY P.Name,YEAR(D.Date), FORMAT(D.Date, 'MMMM', 'ru-RU')
HAVING SUM(D.Amount * S.Price) < 300
ORDER BY 'Год', 'Месяц';
 --5
