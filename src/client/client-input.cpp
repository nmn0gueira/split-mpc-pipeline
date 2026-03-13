#include "Math/gfp.h"
#include "Math/gf2n.h"
#include "Networking/sockets.h"
#include "Networking/ssl_sockets.h"
#include "Tools/int.h"
#include "Math/Setup.h"
#include "Protocols/fake-stuff.h"

#include "Math/gfp.hpp"
#include "Client.hpp"

#include <sodium.h>
#include <iostream>
#include <sstream>
#include <fstream>

template<class T, class U>
void run(const std::vector<string> &strs, Client& client)
{
    std::vector<T> values;
    values.reserve(strs.size());
    for (const auto& s : strs) {
        values.emplace_back(long(round(std::stoi(s))));    // sint
    }

    //one_run<T, U>(long(round(salary_value)), client);
    // sfix with f = 16
    //one_run<T, U>(long(round(salary_value * exp2(16))), client);

    // Run the computation
    client.send_private_inputs<T>(values);
    cout << "Sent private inputs to each SPDZ engine, waiting for result..." << endl;

    std::vector<U> result = client.receive_outputs<T>(4);   // TODO: Output vector should be either adaptable or extra info needs to be specified at the start

    // Get the result back (client_id of winning client)
    for (const auto& r : result)
        cout << "Output : " << r << endl;
}

std::vector<std::string> read_csv_column(const std::string& filename,
                                       std::size_t col_index)
{
    std::vector<std::string> column;
    std::ifstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    std::string line;
    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string cell;
        std::size_t current = 0;

        // split the line on commas
        while (std::getline(ss, cell, ',')) {
            if (current == col_index) {
                column.push_back(cell);
                break;
            }
            ++current;
        }
    }

    return column;
}

int main(int argc, char** argv)
{
    int my_client_id;
    int nparties;
    char* input_file;
    size_t column;
    size_t finish;
    int port_base = 14000;

    if (argc < 5) {
        cout << "Usage is client-input <client identifier> <number of spdz parties> "
           << "<input file> <column index> <finish (0 false, 1 true)> <optional host names..., default localhost> "
           << "<optional spdz party port base number, default 14000>" << endl;
        exit(0);
    }

    my_client_id = atoi(argv[1]);
    nparties = atoi(argv[2]);
    input_file = argv[3];
    column = atoi(argv[4]);
    finish = atoi(argv[5]); // If this is the last client connecting
    vector<string> hostnames(nparties, "localhost");

    std::vector<std::string> strs = read_csv_column(input_file, column);

    /*if (argc > 5)
    {
        if (argc < 5 + nparties)
        {
            cerr << "Not enough hostnames specified";
            exit(1);
        }

        for (int i = 0; i < nparties; i++)
            hostnames[i] = argv[5 + i];
    }

    if (argc > 5 + nparties)
        port_base = atoi(argv[5 + nparties]);
    */
    
    bigint::init_thread();

    // Setup connections from this client to each party socket
    Client client(hostnames, port_base, my_client_id);
    auto& specification = client.specification;
    auto& sockets = client.sockets;
    for (int i = 0; i < nparties; i++)
    {
        octetStream os;
        os.store(finish);
        os.Send(sockets[i]);
    }
    cout << "Finish setup socket connections to SPDZ engines." << endl;

    int type = specification.get<int>();
    switch (type)
    {
    case 'p':
    {
        gfp::init_field(specification.get<bigint>());
        cerr << "using prime " << gfp::pr() << endl;
        run<gfp, gfp>(strs, client);
        break;
    }
    case 'R':
    {
        int R = specification.get<int>();
        int R2 = specification.get<int>();
        if (R != R2)
        {
            cerr << "R (" << R << ") different than R2 (" << R2 << ")." << endl;
        }

        switch (R)
        {
        case 64:
            run<Z2<64>, Z2<64>>(strs, client);
            break;
        case 128:
            //run<Z2<128>, Z2<64>>(strs, client);   // This was the original, but it resulted in errors when assigning the output of client.receive_outputs to a vector<U>, apparently due to conversion errors from Z2<128> to Z2<64>
            run<Z2<128>, Z2<128>>(strs, client);
            break;
        default:
            cerr << R << "-bit ring not implemented";
            exit(1);
        }
        break;
    }
    default:
        cerr << "Type " << type << " not implemented";
        exit(1);
    }

    return 0;
}
