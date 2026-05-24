import { useEffect, useState } from "react";
import { Customer } from "../../domain";
import { CustomerApi } from "../../api";

export const CustomerList = () => {
  const [list, setList] = useState<Customer[]>([]);

  useEffect(() => {
    CustomerApi.getAll().then((res) => setList(res.data));
  }, []);

  return (
    <div>
      <h2>Customers</h2>
      <ul>
        {list.map((c) => (
          <li key={c.id}>
            {c.name} - {c.address}
          </li>
        ))}
      </ul>
      <h3>Create New</h3>
      <CustomerForm />
    </div>
  );
};