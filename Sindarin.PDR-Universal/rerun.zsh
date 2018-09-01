for e in `python src/report.py --list-filenames`
do echo python src/epr_pdr.py -u benchmarks/$e
   echo python src/epr_pdr.py -u benchmarks/safety-only/$e
   echo python src/epr_pdr.py benchmarks/safety-only/$e
done
